/*
 * Tiny CUDA Compiler - Abstract Syntax Tree (AST)
 *
 * Defines the node types used to represent a parsed CUDA kernel.
 * The AST bridges the parser and the PTX code generator.
 *
 * Supported CUDA subset:
 *   - __global__ kernel functions
 *   - Types: void, int, float, int*, float*
 *   - Statements: var decl, assignment, if, while, return, block
 *   - Expressions: arithmetic, comparison, array access, threadIdx/blockIdx/blockDim/gridDim
 */

#ifndef CUDA_AST_H
#define CUDA_AST_H

#include <stdlib.h>
#include <string.h>

/* -----------------------------------------------------------------------
 * Primitive data types
 * ----------------------------------------------------------------------- */
typedef enum {
    DTYPE_VOID,
    DTYPE_INT,
    DTYPE_FLOAT,
    DTYPE_INT_PTR,      /* int*   */
    DTYPE_FLOAT_PTR,    /* float* */
    DTYPE_UNKNOWN
} DataType;

/* -----------------------------------------------------------------------
 * CUDA built-in variable kinds
 * ----------------------------------------------------------------------- */
typedef enum {
    BUILTIN_THREADIDX,
    BUILTIN_BLOCKIDX,
    BUILTIN_BLOCKDIM,
    BUILTIN_GRIDDIM
} BuiltinKind;

/* -----------------------------------------------------------------------
 * Dimension selector
 * ----------------------------------------------------------------------- */
typedef enum { DIM_X = 0, DIM_Y = 1, DIM_Z = 2 } Dimension;

/* -----------------------------------------------------------------------
 * Binary operators
 * ----------------------------------------------------------------------- */
typedef enum {
    BINOP_ADD, BINOP_SUB, BINOP_MUL, BINOP_DIV, BINOP_MOD,
    BINOP_EQ,  BINOP_NE,  BINOP_LT,  BINOP_GT,  BINOP_LE, BINOP_GE,
    BINOP_AND, BINOP_OR
} BinOp;

/* -----------------------------------------------------------------------
 * AST node types
 * ----------------------------------------------------------------------- */
typedef enum {
    NODE_PROGRAM,       /* root: list of kernels         */
    NODE_KERNEL_FUNC,   /* __global__ void name(params){} */
    NODE_PARAM,         /* function parameter             */
    NODE_BLOCK,         /* { stmt* }                      */
    NODE_VAR_DECL,      /* type name [= expr];            */
    NODE_ASSIGN,        /* lval = expr                    */
    NODE_IF,            /* if (cond) then [else]          */
    NODE_WHILE,         /* while (cond) body              */
    NODE_RETURN,        /* return [expr];                 */
    NODE_EXPR_STMT,     /* expr;                          */
    NODE_BINOP,         /* left op right                  */
    NODE_IDENT,         /* variable / identifier          */
    NODE_INT_LIT,       /* integer literal                */
    NODE_FLOAT_LIT,     /* float literal                  */
    NODE_ARRAY_ACCESS,  /* arr[idx]                       */
    NODE_BUILTIN        /* threadIdx.x, blockIdx.y, ...   */
} NodeType;

/* -----------------------------------------------------------------------
 * Dynamic list of AST node pointers
 * ----------------------------------------------------------------------- */
typedef struct ASTNode ASTNode;

typedef struct {
    ASTNode **items;
    int       count;
    int       capacity;
} NodeList;

static inline void nodelist_append(NodeList *list, ASTNode *node)
{
    if (list->count >= list->capacity) {
        list->capacity = list->capacity ? list->capacity * 2 : 8;
        list->items = (ASTNode **)realloc(list->items,
                                          list->capacity * sizeof(ASTNode *));
    }
    list->items[list->count++] = node;
}

/* -----------------------------------------------------------------------
 * The AST node
 * ----------------------------------------------------------------------- */
struct ASTNode {
    NodeType type;
    DataType dtype;     /* resolved type of this expression  */
    int      line;      /* source line (for error messages)  */

    union {
        /* NODE_PROGRAM */
        struct { NodeList kernels; } program;

        /* NODE_KERNEL_FUNC */
        struct {
            char     name[256];
            NodeList params;
            ASTNode *body;
        } kernel_func;

        /* NODE_PARAM */
        struct {
            char     name[256];
            DataType dtype;
        } param;

        /* NODE_BLOCK */
        struct { NodeList stmts; } block;

        /* NODE_VAR_DECL */
        struct {
            char     name[256];
            DataType dtype;
            ASTNode *init;  /* may be NULL */
        } var_decl;

        /* NODE_ASSIGN */
        struct {
            ASTNode *target;
            ASTNode *value;
        } assign;

        /* NODE_IF */
        struct {
            ASTNode *cond;
            ASTNode *then_branch;
            ASTNode *else_branch; /* may be NULL */
        } if_stmt;

        /* NODE_WHILE */
        struct {
            ASTNode *cond;
            ASTNode *body;
        } while_stmt;

        /* NODE_RETURN */
        struct { ASTNode *value; /* may be NULL */ } return_stmt;

        /* NODE_EXPR_STMT */
        struct { ASTNode *expr; } expr_stmt;

        /* NODE_BINOP */
        struct {
            BinOp    op;
            ASTNode *left;
            ASTNode *right;
        } binop;

        /* NODE_IDENT */
        struct { char name[256]; } ident;

        /* NODE_INT_LIT */
        struct { int value; } int_lit;

        /* NODE_FLOAT_LIT */
        struct { float value; } float_lit;

        /* NODE_ARRAY_ACCESS */
        struct {
            char     array_name[256];
            ASTNode *index;
        } array_access;

        /* NODE_BUILTIN – threadIdx.x etc. */
        struct {
            BuiltinKind kind;
            Dimension   dim;
        } builtin;
    };
};

/* -----------------------------------------------------------------------
 * Helper: allocate and zero-initialise a node
 * ----------------------------------------------------------------------- */
static inline ASTNode *ast_new(NodeType type)
{
    ASTNode *n = (ASTNode *)calloc(1, sizeof(ASTNode));
    n->type = type;
    return n;
}

#endif /* CUDA_AST_H */
