/*
 * Tiny CUDA Compiler - PTX Code Generator
 *
 * Walks the AST produced by the parser and emits PTX (Parallel Thread
 * eXecution) assembly – NVIDIA's virtual ISA that is JIT-compiled to
 * native GPU machine code by the driver.
 *
 * PTX Quick Reference
 * ───────────────────
 *  .version 7.5        – PTX ISA version
 *  .target  sm_60      – target compute capability
 *  .address_size 64    – 64-bit pointer model
 *
 *  Register classes:
 *    %p<N>   – predicate (boolean) registers
 *    %r<N>   – 32-bit integer registers  (.b32 / .u32 / .s32)
 *    %rd<N>  – 64-bit registers / pointers (.b64 / .u64 / .s64)
 *    %f<N>   – 32-bit float registers  (.f32)
 *
 *  Key instructions used:
 *    ld.param.<type>   – load a kernel parameter into a register
 *    mov.u32 %r, %tid.x  – read CUDA thread index
 *    mov.u32 %r, %ntid.x – read block dimension
 *    mov.u32 %r, %ctaid.x– read block index
 *    mul.lo.s32 / mul.wide.s32 – integer multiply (32→32 or 32→64)
 *    add.s32 / add.s64   – integer add
 *    add.f32             – float add
 *    setp.<cmp>.<type>   – compare and set predicate
 *    @!%p bra label      – conditional branch (if predicate is false)
 *    ld.global.<type>    – load from GPU global memory
 *    st.global.<type>    – store to GPU global memory
 *    ret                 – return from kernel
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ast.h"

/* -----------------------------------------------------------------------
 * Register types in PTX
 * ----------------------------------------------------------------------- */
typedef enum {
    REG_PRED,   /* %p  – predicate                    */
    REG_B32,    /* %r  – 32-bit integer / pointer      */
    REG_B64,    /* %rd – 64-bit integer / pointer      */
    REG_F32     /* %f  – 32-bit float                  */
} RegType;

#define MAX_VARS 128

/* -----------------------------------------------------------------------
 * Per-kernel code generation state
 * ----------------------------------------------------------------------- */
typedef struct {
    FILE *out;

    /* Register counters – we pre-declare generous amounts at kernel entry */
    int r_count;    /* %r  counter */
    int rd_count;   /* %rd counter */
    int f_count;    /* %f  counter */
    int p_count;    /* %p  counter */

    int label_count;    /* unique label suffix */

    /* Variable/parameter symbol table */
    struct {
        char     name[256];
        RegType  reg_type;
        int      reg_id;
        DataType dtype;     /* original CUDA data type (for pointer elem type) */
    } vars[MAX_VARS];
    int var_count;

    /* Kernel parameter table (subset of vars) */
    struct {
        char     name[256];
        DataType dtype;
        int      reg_id;
        RegType  reg_type;
    } params[32];
    int param_count;

    char kernel_name[256];
} CodeGen;

/* -----------------------------------------------------------------------
 * Utilities
 * ----------------------------------------------------------------------- */
static const char *reg_prefix(RegType t)
{
    switch (t) {
        case REG_PRED: return "%p";
        case REG_B32:  return "%r";
        case REG_B64:  return "%rd";
        case REG_F32:  return "%f";
    }
    return "%r";
}

static int alloc_reg(CodeGen *cg, RegType type)
{
    switch (type) {
        case REG_PRED: return cg->p_count++;
        case REG_B32:  return cg->r_count++;
        case REG_B64:  return cg->rd_count++;
        case REG_F32:  return cg->f_count++;
    }
    return cg->r_count++;
}

static int alloc_label(CodeGen *cg) { return cg->label_count++; }

static RegType dtype_to_regtype(DataType dt)
{
    switch (dt) {
        case DTYPE_FLOAT:
        case DTYPE_FLOAT_PTR: /* pointer itself is 64-bit */
            return (dt == DTYPE_FLOAT) ? REG_F32 : REG_B64;
        case DTYPE_INT_PTR:   return REG_B64;
        case DTYPE_INT:
        default:              return REG_B32;
    }
}

/* Map a DataType to the PTX .param type string */
static const char *param_ptx_type(DataType dt)
{
    switch (dt) {
        case DTYPE_FLOAT_PTR: return ".u64";
        case DTYPE_INT_PTR:   return ".u64";
        case DTYPE_FLOAT:     return ".f32";
        case DTYPE_INT:       return ".u32";
        default:              return ".u32";
    }
}

/* Look up a variable; return register id or -1.  Fills *rt and *dt. */
static int find_var(const CodeGen *cg, const char *name,
                    RegType *rt, DataType *dt)
{
    /* Search local vars first (inner scope wins) */
    for (int i = cg->var_count - 1; i >= 0; i--) {
        if (strcmp(cg->vars[i].name, name) == 0) {
            if (rt) *rt = cg->vars[i].reg_type;
            if (dt) *dt = cg->vars[i].dtype;
            return cg->vars[i].reg_id;
        }
    }
    /* Then kernel parameters */
    for (int i = 0; i < cg->param_count; i++) {
        if (strcmp(cg->params[i].name, name) == 0) {
            if (rt) *rt = cg->params[i].reg_type;
            if (dt) *dt = cg->params[i].dtype;
            return cg->params[i].reg_id;
        }
    }
    return -1;
}

/* PTX load/store type suffix for an element pointed to by dtype */
static const char *elem_type_suffix(DataType ptr_dtype, RegType *elem_rt)
{
    if (ptr_dtype == DTYPE_FLOAT_PTR) {
        if (elem_rt) *elem_rt = REG_F32;
        return "f32";
    }
    /* default: int */
    if (elem_rt) *elem_rt = REG_B32;
    return "s32";
}

/* -----------------------------------------------------------------------
 * Expression code generation
 *
 * Emits PTX instructions and returns the register id that holds the
 * result.  The caller receives the register type via *rtype.
 * ----------------------------------------------------------------------- */
static int gen_expr(CodeGen *cg, ASTNode *node, RegType *rtype);

static int gen_expr(CodeGen *cg, ASTNode *node, RegType *rtype)
{
    if (!node) {
        if (rtype) *rtype = REG_B32;
        int r = alloc_reg(cg, REG_B32);
        fprintf(cg->out, "\tmov.u32\t\t%s%d, 0;\n", reg_prefix(REG_B32), r);
        return r;
    }

    switch (node->type) {

    /* ── Integer literal ─────────────────────────────────────────────── */
    case NODE_INT_LIT: {
        int reg = alloc_reg(cg, REG_B32);
        fprintf(cg->out, "\tmov.u32\t\t%s%d, %d;\n",
                reg_prefix(REG_B32), reg, node->int_lit.value);
        if (rtype) *rtype = REG_B32;
        return reg;
    }

    /* ── Float literal ───────────────────────────────────────────────── */
    case NODE_FLOAT_LIT: {
        int reg = alloc_reg(cg, REG_F32);
        /* PTX represents floats as 0F<hex32> for exact bit patterns */
        unsigned int bits;
        memcpy(&bits, &node->float_lit.value, sizeof(bits));
        fprintf(cg->out, "\tmov.f32\t\t%s%d, 0F%08X;\n",
                reg_prefix(REG_F32), reg, bits);
        if (rtype) *rtype = REG_F32;
        return reg;
    }

    /* ── CUDA built-in (threadIdx.x, blockIdx.y, …) ─────────────────── */
    case NODE_BUILTIN: {
        static const char *dims[] = {"x", "y", "z"};
        int reg = alloc_reg(cg, REG_B32);
        switch (node->builtin.kind) {
            case BUILTIN_THREADIDX:
                fprintf(cg->out, "\tmov.u32\t\t%s%d, %%tid.%s;\n",
                        reg_prefix(REG_B32), reg, dims[node->builtin.dim]);
                break;
            case BUILTIN_BLOCKIDX:
                fprintf(cg->out, "\tmov.u32\t\t%s%d, %%ctaid.%s;\n",
                        reg_prefix(REG_B32), reg, dims[node->builtin.dim]);
                break;
            case BUILTIN_BLOCKDIM:
                fprintf(cg->out, "\tmov.u32\t\t%s%d, %%ntid.%s;\n",
                        reg_prefix(REG_B32), reg, dims[node->builtin.dim]);
                break;
            case BUILTIN_GRIDDIM:
                fprintf(cg->out, "\tmov.u32\t\t%s%d, %%nctaid.%s;\n",
                        reg_prefix(REG_B32), reg, dims[node->builtin.dim]);
                break;
        }
        if (rtype) *rtype = REG_B32;
        return reg;
    }

    /* ── Identifier ──────────────────────────────────────────────────── */
    case NODE_IDENT: {
        RegType rt;
        DataType dt;
        int reg = find_var(cg, node->ident.name, &rt, &dt);
        if (reg < 0) {
            fprintf(stderr, "Codegen error: undefined variable '%s'\n",
                    node->ident.name);
            reg = alloc_reg(cg, REG_B32);
            rt  = REG_B32;
        }
        if (rtype) *rtype = rt;
        return reg;
    }

    /* ── Array access: arr[idx] ──────────────────────────────────────── */
    case NODE_ARRAY_ACCESS: {
        /*
         * PTX sequence:
         *   (1) mul.wide.s32  %rd_off, %r_idx, 4    -- byte offset
         *   (2) add.s64       %rd_addr, %rd_base, %rd_off
         *   (3) ld.global.<t> %val, [%rd_addr]
         */
        RegType  ptr_rt;
        DataType ptr_dt;
        int ptr_reg = find_var(cg, node->array_access.array_name,
                               &ptr_rt, &ptr_dt);
        if (ptr_reg < 0) {
            fprintf(stderr, "Codegen error: undefined array '%s'\n",
                    node->array_access.array_name);
            ptr_reg = alloc_reg(cg, REG_B64);
            ptr_rt  = REG_B64;
            ptr_dt  = DTYPE_INT_PTR;
        }

        RegType idx_rt;
        int idx_reg = gen_expr(cg, node->array_access.index, &idx_rt);

        /* Byte offset = index * 4  (float and int are both 4 bytes) */
        int off_reg = alloc_reg(cg, REG_B64);
        fprintf(cg->out, "\tmul.wide.s32\t%s%d, %s%d, 4;\n",
                reg_prefix(REG_B64), off_reg,
                reg_prefix(idx_rt),  idx_reg);

        /* Address = base pointer + offset */
        int addr_reg = alloc_reg(cg, REG_B64);
        fprintf(cg->out, "\tadd.s64\t\t%s%d, %s%d, %s%d;\n",
                reg_prefix(REG_B64), addr_reg,
                reg_prefix(REG_B64), ptr_reg,
                reg_prefix(REG_B64), off_reg);

        /* Determine element type from the pointer's data type */
        RegType elem_rt;
        const char *suffix = elem_type_suffix(ptr_dt, &elem_rt);

        int val_reg = alloc_reg(cg, elem_rt);
        fprintf(cg->out, "\tld.global.%s\t%s%d, [%s%d];\n",
                suffix,
                reg_prefix(elem_rt), val_reg,
                reg_prefix(REG_B64), addr_reg);

        if (rtype) *rtype = elem_rt;
        return val_reg;
    }

    /* ── Binary operation ────────────────────────────────────────────── */
    case NODE_BINOP: {
        RegType lt, rt2;
        int lreg = gen_expr(cg, node->binop.left,  &lt);
        int rreg = gen_expr(cg, node->binop.right, &rt2);

        /* Comparison → predicate register */
        if (node->binop.op >= BINOP_EQ && node->binop.op <= BINOP_GE) {
            int preg = alloc_reg(cg, REG_PRED);
            const char *cmp;
            switch (node->binop.op) {
                case BINOP_EQ: cmp = "eq"; break;
                case BINOP_NE: cmp = "ne"; break;
                case BINOP_LT: cmp = "lt"; break;
                case BINOP_GT: cmp = "gt"; break;
                case BINOP_LE: cmp = "le"; break;
                case BINOP_GE: cmp = "ge"; break;
                default:       cmp = "eq"; break;
            }
            const char *ptx_t = (lt == REG_F32) ? "f32" : "s32";
            fprintf(cg->out, "\tsetp.%s.%s\t%s%d, %s%d, %s%d;\n",
                    cmp, ptx_t,
                    reg_prefix(REG_PRED), preg,
                    reg_prefix(lt),       lreg,
                    reg_prefix(rt2),      rreg);
            if (rtype) *rtype = REG_PRED;
            return preg;
        }

        /* Logical AND / OR on predicates */
        if (node->binop.op == BINOP_AND || node->binop.op == BINOP_OR) {
            int preg = alloc_reg(cg, REG_PRED);
            const char *op = (node->binop.op == BINOP_AND) ? "and" : "or";
            /* Convert integer operands to predicates if needed */
            int pl = lreg, pr2 = rreg;
            if (lt != REG_PRED) {
                pl = alloc_reg(cg, REG_PRED);
                fprintf(cg->out, "\tsetp.ne.s32\t%s%d, %s%d, 0;\n",
                        reg_prefix(REG_PRED), pl, reg_prefix(lt), lreg);
            }
            if (rt2 != REG_PRED) {
                pr2 = alloc_reg(cg, REG_PRED);
                fprintf(cg->out, "\tsetp.ne.s32\t%s%d, %s%d, 0;\n",
                        reg_prefix(REG_PRED), pr2, reg_prefix(rt2), rreg);
            }
            fprintf(cg->out, "\t%s.pred\t\t%s%d, %s%d, %s%d;\n",
                    op,
                    reg_prefix(REG_PRED), preg,
                    reg_prefix(REG_PRED), pl,
                    reg_prefix(REG_PRED), pr2);
            if (rtype) *rtype = REG_PRED;
            return preg;
        }

        /* Arithmetic */
        RegType res_type = (lt == REG_F32 || rt2 == REG_F32) ? REG_F32 : REG_B32;
        int res_reg = alloc_reg(cg, res_type);
        const char *pt = (res_type == REG_F32) ? "f32" : "s32";

        switch (node->binop.op) {
            case BINOP_ADD:
                fprintf(cg->out, "\tadd.%s\t\t%s%d, %s%d, %s%d;\n",
                        pt,
                        reg_prefix(res_type), res_reg,
                        reg_prefix(lt),       lreg,
                        reg_prefix(rt2),      rreg);
                break;
            case BINOP_SUB:
                fprintf(cg->out, "\tsub.%s\t\t%s%d, %s%d, %s%d;\n",
                        pt,
                        reg_prefix(res_type), res_reg,
                        reg_prefix(lt),       lreg,
                        reg_prefix(rt2),      rreg);
                break;
            case BINOP_MUL:
                if (res_type == REG_F32)
                    fprintf(cg->out, "\tmul.f32\t\t%s%d, %s%d, %s%d;\n",
                            reg_prefix(res_type), res_reg,
                            reg_prefix(lt),       lreg,
                            reg_prefix(rt2),      rreg);
                else
                    fprintf(cg->out, "\tmul.lo.s32\t%s%d, %s%d, %s%d;\n",
                            reg_prefix(res_type), res_reg,
                            reg_prefix(lt),       lreg,
                            reg_prefix(rt2),      rreg);
                break;
            case BINOP_DIV:
                if (res_type == REG_F32)
                    fprintf(cg->out, "\tdiv.rn.f32\t%s%d, %s%d, %s%d;\n",
                            reg_prefix(res_type), res_reg,
                            reg_prefix(lt),       lreg,
                            reg_prefix(rt2),      rreg);
                else
                    fprintf(cg->out, "\tdiv.s32\t\t%s%d, %s%d, %s%d;\n",
                            reg_prefix(res_type), res_reg,
                            reg_prefix(lt),       lreg,
                            reg_prefix(rt2),      rreg);
                break;
            case BINOP_MOD:
                fprintf(cg->out, "\trem.s32\t\t%s%d, %s%d, %s%d;\n",
                        reg_prefix(res_type), res_reg,
                        reg_prefix(lt),       lreg,
                        reg_prefix(rt2),      rreg);
                break;
            default:
                break;
        }

        if (rtype) *rtype = res_type;
        return res_reg;
    }

    default:
        if (rtype) *rtype = REG_B32;
        return alloc_reg(cg, REG_B32);
    }
}

/* -----------------------------------------------------------------------
 * Statement code generation
 * ----------------------------------------------------------------------- */
static void gen_stmt(CodeGen *cg, ASTNode *node);

static void gen_stmt(CodeGen *cg, ASTNode *node)
{
    if (!node) return;

    switch (node->type) {

    /* ── Variable declaration ────────────────────────────────────────── */
    case NODE_VAR_DECL: {
        RegType rt  = dtype_to_regtype(node->var_decl.dtype);
        int     reg = alloc_reg(cg, rt);

        /* Register in local symbol table */
        int vi = cg->var_count++;
        snprintf(cg->vars[vi].name, sizeof(cg->vars[vi].name),
                 "%s", node->var_decl.name);
        cg->vars[vi].name[255] = '\0';
        cg->vars[vi].reg_type  = rt;
        cg->vars[vi].reg_id    = reg;
        cg->vars[vi].dtype     = node->var_decl.dtype;

        if (node->var_decl.init) {
            RegType src_rt;
            int src_reg = gen_expr(cg, node->var_decl.init, &src_rt);
            /* Move result into the declared register */
            const char *mv_type;
            switch (rt) {
                case REG_F32: mv_type = "f32"; break;
                case REG_B64: mv_type = "b64"; break;
                default:      mv_type = "b32"; break;
            }
            if (src_rt != rt && src_rt == REG_B32 && rt == REG_B64) {
                /* sign-extend 32-bit to 64-bit */
                fprintf(cg->out, "\tcvt.s64.s32\t%s%d, %s%d;\n",
                        reg_prefix(rt),     reg,
                        reg_prefix(src_rt), src_reg);
            } else {
                fprintf(cg->out, "\tmov.%s\t\t%s%d, %s%d;\n",
                        mv_type,
                        reg_prefix(rt),     reg,
                        reg_prefix(src_rt), src_reg);
            }
        }
        break;
    }

    /* ── Assignment ──────────────────────────────────────────────────── */
    case NODE_ASSIGN: {
        ASTNode *target = node->assign.target;

        /* arr[idx] = expr  → st.global */
        if (target->type == NODE_ARRAY_ACCESS) {
            RegType  ptr_rt;
            DataType ptr_dt;
            int ptr_reg = find_var(cg, target->array_access.array_name,
                                   &ptr_rt, &ptr_dt);
            if (ptr_reg < 0) {
                fprintf(stderr, "Codegen error: undefined array '%s'\n",
                        target->array_access.array_name);
                break;
            }

            RegType idx_rt;
            int idx_reg = gen_expr(cg, target->array_access.index, &idx_rt);

            int off_reg = alloc_reg(cg, REG_B64);
            fprintf(cg->out, "\tmul.wide.s32\t%s%d, %s%d, 4;\n",
                    reg_prefix(REG_B64), off_reg,
                    reg_prefix(idx_rt),  idx_reg);

            int addr_reg = alloc_reg(cg, REG_B64);
            fprintf(cg->out, "\tadd.s64\t\t%s%d, %s%d, %s%d;\n",
                    reg_prefix(REG_B64), addr_reg,
                    reg_prefix(REG_B64), ptr_reg,
                    reg_prefix(REG_B64), off_reg);

            RegType val_rt;
            int val_reg = gen_expr(cg, node->assign.value, &val_rt);

            RegType elem_rt;
            const char *suffix = elem_type_suffix(ptr_dt, &elem_rt);
            /* If val is float and we're storing to float*, no conversion needed */
            fprintf(cg->out, "\tst.global.%s\t[%s%d], %s%d;\n",
                    suffix,
                    reg_prefix(REG_B64), addr_reg,
                    reg_prefix(val_rt),  val_reg);
            break;
        }

        /* ident = expr  → mov */
        if (target->type == NODE_IDENT) {
            RegType  dst_rt;
            DataType dst_dt;
            int dst_reg = find_var(cg, target->ident.name, &dst_rt, &dst_dt);
            if (dst_reg < 0) {
                fprintf(stderr, "Codegen error: undefined variable '%s'\n",
                        target->ident.name);
                break;
            }
            RegType src_rt;
            int src_reg = gen_expr(cg, node->assign.value, &src_rt);
            const char *mv;
            switch (dst_rt) {
                case REG_F32: mv = "f32"; break;
                case REG_B64: mv = "b64"; break;
                default:      mv = "b32"; break;
            }
            fprintf(cg->out, "\tmov.%s\t\t%s%d, %s%d;\n",
                    mv,
                    reg_prefix(dst_rt), dst_reg,
                    reg_prefix(src_rt), src_reg);
        }
        break;
    }

    /* ── Expression statement ────────────────────────────────────────── */
    case NODE_EXPR_STMT: {
        ASTNode *expr = node->expr_stmt.expr;
        /*
         * If the expression is an assignment (arr[i] = val or var = val),
         * delegate to the NODE_ASSIGN handler which emits store/move.
         * Otherwise just evaluate the expression for its side effects.
         */
        if (expr->type == NODE_ASSIGN) {
            gen_stmt(cg, expr);
        } else {
            RegType rt;
            gen_expr(cg, expr, &rt);
        }
        break;
    }

    /* ── if statement ────────────────────────────────────────────────── */
    case NODE_IF: {
        int lbl = alloc_label(cg);

        RegType ctype;
        int cond_reg = gen_expr(cg, node->if_stmt.cond, &ctype);

        /* Ensure we have a predicate */
        int pred_reg;
        if (ctype != REG_PRED) {
            pred_reg = alloc_reg(cg, REG_PRED);
            fprintf(cg->out, "\tsetp.ne.s32\t%s%d, %s%d, 0;\n",
                    reg_prefix(REG_PRED), pred_reg,
                    reg_prefix(ctype),    cond_reg);
        } else {
            pred_reg = cond_reg;
        }

        if (node->if_stmt.else_branch) {
            fprintf(cg->out, "\t@!%s%d bra\tBB_else_%d;\n",
                    reg_prefix(REG_PRED), pred_reg, lbl);
            gen_stmt(cg, node->if_stmt.then_branch);
            fprintf(cg->out, "\tbra\t\tBB_end_%d;\n", lbl);
            fprintf(cg->out, "BB_else_%d:\n", lbl);
            gen_stmt(cg, node->if_stmt.else_branch);
        } else {
            fprintf(cg->out, "\t@!%s%d bra\tBB_end_%d;\n",
                    reg_prefix(REG_PRED), pred_reg, lbl);
            gen_stmt(cg, node->if_stmt.then_branch);
        }
        fprintf(cg->out, "BB_end_%d:\n", lbl);
        break;
    }

    /* ── while statement ─────────────────────────────────────────────── */
    case NODE_WHILE: {
        int lbl = alloc_label(cg);
        fprintf(cg->out, "BB_while_%d:\n", lbl);

        RegType ctype;
        int cond_reg = gen_expr(cg, node->while_stmt.cond, &ctype);

        int pred_reg;
        if (ctype != REG_PRED) {
            pred_reg = alloc_reg(cg, REG_PRED);
            fprintf(cg->out, "\tsetp.ne.s32\t%s%d, %s%d, 0;\n",
                    reg_prefix(REG_PRED), pred_reg,
                    reg_prefix(ctype),    cond_reg);
        } else {
            pred_reg = cond_reg;
        }

        fprintf(cg->out, "\t@!%s%d bra\tBB_wend_%d;\n",
                reg_prefix(REG_PRED), pred_reg, lbl);
        gen_stmt(cg, node->while_stmt.body);
        fprintf(cg->out, "\tbra\t\tBB_while_%d;\n", lbl);
        fprintf(cg->out, "BB_wend_%d:\n", lbl);
        break;
    }

    /* ── Block ───────────────────────────────────────────────────────── */
    case NODE_BLOCK:
        for (int i = 0; i < node->block.stmts.count; i++)
            gen_stmt(cg, node->block.stmts.items[i]);
        break;

    /* ── return ──────────────────────────────────────────────────────── */
    case NODE_RETURN:
        if (node->return_stmt.value) {
            RegType rt;
            gen_expr(cg, node->return_stmt.value, &rt);
        }
        fprintf(cg->out, "\tret;\n");
        break;

    default:
        break;
    }
}

/* -----------------------------------------------------------------------
 * Kernel code generation
 * ----------------------------------------------------------------------- */
static void gen_kernel(FILE *out, ASTNode *kernel)
{
    CodeGen cg;
    memset(&cg, 0, sizeof(cg));
    cg.out = out;
    snprintf(cg.kernel_name, sizeof(cg.kernel_name),
             "%s", kernel->kernel_func.name);

    /* ── Collect parameter information ─────────────────────────────── */
    cg.param_count = kernel->kernel_func.params.count;
    if (cg.param_count > 32) cg.param_count = 32;

    for (int i = 0; i < cg.param_count; i++) {
        ASTNode *param = kernel->kernel_func.params.items[i];
        snprintf(cg.params[i].name, sizeof(cg.params[i].name),
                 "%s", param->param.name);
        cg.params[i].dtype    = param->param.dtype;
        cg.params[i].reg_type = dtype_to_regtype(param->param.dtype);
        cg.params[i].reg_id   = alloc_reg(&cg, cg.params[i].reg_type);
    }

    /* ── Emit kernel header ─────────────────────────────────────────── */
    fprintf(out, "\n.visible .entry %s(\n", kernel->kernel_func.name);
    for (int i = 0; i < cg.param_count; i++) {
        fprintf(out, "\t.param %s\t%s_param_%d",
                param_ptx_type(cg.params[i].dtype),
                kernel->kernel_func.name, i);
        fprintf(out, "%s\n", (i < cg.param_count - 1) ? "," : "");
    }
    fprintf(out, ")\n{\n");

    /*
     * We declare generous register budgets upfront.
     * A production compiler would do a second pass to count exact usage.
     */
    fprintf(out, "\t.reg .pred\t%%p<32>;\n");
    fprintf(out, "\t.reg .f32\t%%f<64>;\n");
    fprintf(out, "\t.reg .b32\t%%r<64>;\n");
    fprintf(out, "\t.reg .b64\t%%rd<64>;\n");
    fprintf(out, "\n");

    /* ── Load parameters from .param space ──────────────────────────── */
    for (int i = 0; i < cg.param_count; i++) {
        const char *ptx_t = param_ptx_type(cg.params[i].dtype);
        RegType     rt    = cg.params[i].reg_type;
        int         reg   = cg.params[i].reg_id;
        fprintf(out, "\tld.param%s\t%s%d, [%s_param_%d];\n",
                ptx_t,
                reg_prefix(rt), reg,
                kernel->kernel_func.name, i);
    }
    fprintf(out, "\n");

    /* ── Generate body ──────────────────────────────────────────────── */
    gen_stmt(&cg, kernel->kernel_func.body);

    /* Ensure there is always a terminal ret */
    fprintf(out, "\tret;\n");
    fprintf(out, "}\n");
}

/* -----------------------------------------------------------------------
 * Public entry point
 * ----------------------------------------------------------------------- */
void codegen(ASTNode *program, FILE *out, const char *target_arch)
{
    fprintf(out, "//\n");
    fprintf(out, "// Generated by tiny-cuda-compiler\n");
    fprintf(out, "//\n\n");
    fprintf(out, ".version 7.5\n");
    fprintf(out, ".target %s\n", target_arch ? target_arch : "sm_60");
    fprintf(out, ".address_size 64\n");

    for (int i = 0; i < program->program.kernels.count; i++)
        gen_kernel(out, program->program.kernels.items[i]);
}
