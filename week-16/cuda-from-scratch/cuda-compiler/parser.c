/*
 * Tiny CUDA Compiler - Recursive Descent Parser
 *
 * Parses a CUDA source string (already tokenised by the lexer) into an AST.
 *
 * Grammar handled (simplified):
 *
 *   program         ::= ( kernel_func | <skip> )*
 *   kernel_func     ::= '__global__' 'void' IDENT '(' param_list ')' block
 *   param_list      ::= ( param ( ',' param )* )?
 *   param           ::= ['const'] type IDENT
 *   type            ::= ('int'|'float'|'unsigned') ['*']
 *   block           ::= '{' stmt* '}'
 *   stmt            ::= var_decl | if_stmt | while_stmt | return_stmt
 *                      | block   | expr_stmt
 *   var_decl        ::= type IDENT ['=' expr] ';'
 *   if_stmt         ::= 'if' '(' expr ')' block ['else' block]
 *   while_stmt      ::= 'while' '(' expr ')' block
 *   return_stmt     ::= 'return' [expr] ';'
 *   expr_stmt       ::= expr ';'
 *   expr            ::= assignment
 *   assignment      ::= or_expr ['=' assignment]
 *   or_expr         ::= and_expr  ('||' and_expr)*
 *   and_expr        ::= eq_expr   ('&&' eq_expr)*
 *   eq_expr         ::= rel_expr  (('=='|'!=') rel_expr)*
 *   rel_expr        ::= add_expr  (('<'|'>'|'<='|'>=') add_expr)*
 *   add_expr        ::= mul_expr  (('+'|'-') mul_expr)*
 *   mul_expr        ::= unary     (('*'|'/'|'%') unary)*
 *   unary           ::= '-' unary | primary
 *   primary         ::= INT_LIT | FLOAT_LIT
 *                      | builtin ('.' DIM)
 *                      | IDENT ('[' expr ']')?
 *                      | '(' expr ')'
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lexer.h"
#include "ast.h"

/* -----------------------------------------------------------------------
 * Parser state
 * ----------------------------------------------------------------------- */
typedef struct {
    Lexer *lex;
    Token  current;
    int    had_error;
} Parser;

/* -----------------------------------------------------------------------
 * Helpers
 * ----------------------------------------------------------------------- */
static void parse_error(Parser *p, const char *msg)
{
    fprintf(stderr, "Parse error at line %d col %d: %s (got '%s')\n",
            p->current.line, p->current.col, msg, p->current.value);
    p->had_error = 1;
}

static Token advance(Parser *p)
{
    p->current = lexer_next(p->lex);
    return p->current;
}

static int check(Parser *p, TokenType t)  { return p->current.type == t; }

static Token expect(Parser *p, TokenType t)
{
    if (!check(p, t)) {
        char msg[256];
        snprintf(msg, sizeof(msg), "expected '%s'", token_type_name(t));
        parse_error(p, msg);
    }
    Token tok = p->current;
    advance(p);
    return tok;
}

static int match(Parser *p, TokenType t)
{
    if (check(p, t)) { advance(p); return 1; }
    return 0;
}

/* -----------------------------------------------------------------------
 * Forward declarations
 * ----------------------------------------------------------------------- */
static ASTNode *parse_expr (Parser *p);
static ASTNode *parse_stmt (Parser *p);
static ASTNode *parse_block(Parser *p);

/* -----------------------------------------------------------------------
 * Type parsing
 *
 * Returns the DataType and sets *is_pointer if a '*' follows.
 * ----------------------------------------------------------------------- */
static DataType parse_type(Parser *p, int *is_pointer)
{
    *is_pointer = 0;
    DataType dt = DTYPE_UNKNOWN;

    if      (check(p, TOK_INT))      { advance(p); dt = DTYPE_INT;   }
    else if (check(p, TOK_FLOAT))    { advance(p); dt = DTYPE_FLOAT; }
    else if (check(p, TOK_VOID))     { advance(p); dt = DTYPE_VOID;  }
    else if (check(p, TOK_UNSIGNED)) {
        advance(p);
        if (check(p, TOK_INT)) advance(p);
        dt = DTYPE_INT;
    }

    if (check(p, TOK_STAR)) {
        advance(p);
        *is_pointer = 1;
        if      (dt == DTYPE_INT)   dt = DTYPE_INT_PTR;
        else if (dt == DTYPE_FLOAT) dt = DTYPE_FLOAT_PTR;
    }
    return dt;
}

/* -----------------------------------------------------------------------
 * Expression parsing (recursive descent, operator precedence)
 * ----------------------------------------------------------------------- */

/* primary: literal, built-in, ident, array-access, paren-expr */
static ASTNode *parse_primary(Parser *p)
{
    ASTNode *node;

    /* Integer literal */
    if (check(p, TOK_INT_LIT)) {
        node = ast_new(NODE_INT_LIT);
        node->int_lit.value = atoi(p->current.value);
        node->dtype = DTYPE_INT;
        node->line  = p->current.line;
        advance(p);
        return node;
    }

    /* Float literal */
    if (check(p, TOK_FLOAT_LIT)) {
        node = ast_new(NODE_FLOAT_LIT);
        node->float_lit.value = (float)atof(p->current.value);
        node->dtype = DTYPE_FLOAT;
        node->line  = p->current.line;
        advance(p);
        return node;
    }

    /* CUDA built-in variable: threadIdx / blockIdx / blockDim / gridDim */
    if (check(p, TOK_THREADIDX) || check(p, TOK_BLOCKIDX) ||
        check(p, TOK_BLOCKDIM)  || check(p, TOK_GRIDDIM)) {
        node = ast_new(NODE_BUILTIN);
        node->dtype = DTYPE_INT;
        node->line  = p->current.line;
        switch (p->current.type) {
            case TOK_THREADIDX: node->builtin.kind = BUILTIN_THREADIDX; break;
            case TOK_BLOCKIDX:  node->builtin.kind = BUILTIN_BLOCKIDX;  break;
            case TOK_BLOCKDIM:  node->builtin.kind = BUILTIN_BLOCKDIM;  break;
            default:            node->builtin.kind = BUILTIN_GRIDDIM;   break;
        }
        advance(p);
        /* Dimension selector must follow */
        if      (check(p, TOK_DOT_X)) { node->builtin.dim = DIM_X; advance(p); }
        else if (check(p, TOK_DOT_Y)) { node->builtin.dim = DIM_Y; advance(p); }
        else if (check(p, TOK_DOT_Z)) { node->builtin.dim = DIM_Z; advance(p); }
        else { parse_error(p, "expected .x, .y, or .z after built-in variable"); }
        return node;
    }

    /* Identifier or array access */
    if (check(p, TOK_IDENT)) {
        char name[256];
        int  line = p->current.line;
        strncpy(name, p->current.value, 255);
        name[255] = '\0';
        advance(p);

        if (check(p, TOK_LBRACKET)) {
            advance(p);
            node = ast_new(NODE_ARRAY_ACCESS);
            node->line = line;
            snprintf(node->array_access.array_name,
                     sizeof(node->array_access.array_name), "%s", name);
            node->array_access.index = parse_expr(p);
            expect(p, TOK_RBRACKET);
            return node;
        }

        node = ast_new(NODE_IDENT);
        node->line = line;
        snprintf(node->ident.name, sizeof(node->ident.name), "%s", name);
        return node;
    }

    /* Parenthesised expression */
    if (check(p, TOK_LPAREN)) {
        advance(p);
        node = parse_expr(p);
        expect(p, TOK_RPAREN);
        return node;
    }

    parse_error(p, "unexpected token in expression");
    advance(p);
    /* Return a dummy zero literal so the parser can continue */
    node = ast_new(NODE_INT_LIT);
    node->int_lit.value = 0;
    node->dtype = DTYPE_INT;
    return node;
}

/* unary: -expr */
static ASTNode *parse_unary(Parser *p)
{
    if (check(p, TOK_MINUS)) {
        int line = p->current.line;
        advance(p);
        ASTNode *sub  = parse_unary(p);
        ASTNode *zero = ast_new(NODE_INT_LIT);
        zero->int_lit.value = 0;
        zero->dtype = DTYPE_INT;
        ASTNode *node = ast_new(NODE_BINOP);
        node->line     = line;
        node->binop.op    = BINOP_SUB;
        node->binop.left  = zero;
        node->binop.right = sub;
        return node;
    }
    return parse_primary(p);
}

/* mul_expr: unary ( ('*' | '/' | '%') unary )* */
static ASTNode *parse_mul(Parser *p)
{
    ASTNode *left = parse_unary(p);
    while (check(p, TOK_STAR) || check(p, TOK_SLASH) || check(p, TOK_PERCENT)) {
        BinOp op;
        if      (check(p, TOK_STAR))    op = BINOP_MUL;
        else if (check(p, TOK_SLASH))   op = BINOP_DIV;
        else                            op = BINOP_MOD;
        int line = p->current.line;
        advance(p);
        ASTNode *right = parse_unary(p);
        ASTNode *node  = ast_new(NODE_BINOP);
        node->line     = line;
        node->binop.op    = op;
        node->binop.left  = left;
        node->binop.right = right;
        left = node;
    }
    return left;
}

/* add_expr: mul_expr ( ('+' | '-') mul_expr )* */
static ASTNode *parse_add(Parser *p)
{
    ASTNode *left = parse_mul(p);
    while (check(p, TOK_PLUS) || check(p, TOK_MINUS)) {
        BinOp op   = check(p, TOK_PLUS) ? BINOP_ADD : BINOP_SUB;
        int   line = p->current.line;
        advance(p);
        ASTNode *right = parse_mul(p);
        ASTNode *node  = ast_new(NODE_BINOP);
        node->line     = line;
        node->binop.op    = op;
        node->binop.left  = left;
        node->binop.right = right;
        left = node;
    }
    return left;
}

/* rel_expr: add_expr ( ('<' | '>' | '<=' | '>=') add_expr )* */
static ASTNode *parse_rel(Parser *p)
{
    ASTNode *left = parse_add(p);
    while (check(p, TOK_LT) || check(p, TOK_GT) ||
           check(p, TOK_LE) || check(p, TOK_GE)) {
        BinOp op;
        if      (check(p, TOK_LT)) op = BINOP_LT;
        else if (check(p, TOK_GT)) op = BINOP_GT;
        else if (check(p, TOK_LE)) op = BINOP_LE;
        else                       op = BINOP_GE;
        int line = p->current.line;
        advance(p);
        ASTNode *right = parse_add(p);
        ASTNode *node  = ast_new(NODE_BINOP);
        node->line     = line;
        node->binop.op    = op;
        node->binop.left  = left;
        node->binop.right = right;
        left = node;
    }
    return left;
}

/* eq_expr: rel_expr ( ('==' | '!=') rel_expr )* */
static ASTNode *parse_eq(Parser *p)
{
    ASTNode *left = parse_rel(p);
    while (check(p, TOK_EQ) || check(p, TOK_NE)) {
        BinOp op   = check(p, TOK_EQ) ? BINOP_EQ : BINOP_NE;
        int   line = p->current.line;
        advance(p);
        ASTNode *right = parse_rel(p);
        ASTNode *node  = ast_new(NODE_BINOP);
        node->line     = line;
        node->binop.op    = op;
        node->binop.left  = left;
        node->binop.right = right;
        left = node;
    }
    return left;
}

/* and_expr: eq_expr ('&&' eq_expr)* */
static ASTNode *parse_and(Parser *p)
{
    ASTNode *left = parse_eq(p);
    while (check(p, TOK_AND)) {
        int line = p->current.line;
        advance(p);
        ASTNode *right = parse_eq(p);
        ASTNode *node  = ast_new(NODE_BINOP);
        node->line     = line;
        node->binop.op    = BINOP_AND;
        node->binop.left  = left;
        node->binop.right = right;
        left = node;
    }
    return left;
}

/* or_expr: and_expr ('||' and_expr)* */
static ASTNode *parse_or(Parser *p)
{
    ASTNode *left = parse_and(p);
    while (check(p, TOK_OR)) {
        int line = p->current.line;
        advance(p);
        ASTNode *right = parse_and(p);
        ASTNode *node  = ast_new(NODE_BINOP);
        node->line     = line;
        node->binop.op    = BINOP_OR;
        node->binop.left  = left;
        node->binop.right = right;
        left = node;
    }
    return left;
}

/* assignment: or_expr ['=' assignment]  (right-associative) */
static ASTNode *parse_expr(Parser *p)
{
    ASTNode *left = parse_or(p);
    if (check(p, TOK_ASSIGN)) {
        int line = p->current.line;
        advance(p);
        ASTNode *node = ast_new(NODE_ASSIGN);
        node->line           = line;
        node->assign.target  = left;
        node->assign.value   = parse_expr(p); /* right-associative */
        return node;
    }
    return left;
}

/* -----------------------------------------------------------------------
 * Statement parsing
 * ----------------------------------------------------------------------- */

/* block: '{' stmt* '}' */
static ASTNode *parse_block(Parser *p)
{
    expect(p, TOK_LBRACE);
    ASTNode *node = ast_new(NODE_BLOCK);
    node->line    = p->current.line;
    while (!check(p, TOK_RBRACE) && !check(p, TOK_EOF)) {
        ASTNode *stmt = parse_stmt(p);
        if (stmt) nodelist_append(&node->block.stmts, stmt);
    }
    expect(p, TOK_RBRACE);
    return node;
}

static ASTNode *parse_stmt(Parser *p)
{
    /* var_decl: type IDENT ['=' expr] ';' */
    if (check(p, TOK_INT) || check(p, TOK_FLOAT) || check(p, TOK_UNSIGNED)) {
        int is_ptr;
        int line = p->current.line;
        DataType dt = parse_type(p, &is_ptr);

        if (!check(p, TOK_IDENT)) {
            parse_error(p, "expected variable name after type");
            return NULL;
        }
        ASTNode *node = ast_new(NODE_VAR_DECL);
        node->line = line;
        snprintf(node->var_decl.name, sizeof(node->var_decl.name),
                 "%s", p->current.value);
        node->var_decl.dtype = dt;
        advance(p);

        if (match(p, TOK_ASSIGN))
            node->var_decl.init = parse_expr(p);

        expect(p, TOK_SEMICOLON);
        return node;
    }

    /* if_stmt */
    if (check(p, TOK_IF)) {
        int line = p->current.line;
        advance(p);
        expect(p, TOK_LPAREN);
        ASTNode *node = ast_new(NODE_IF);
        node->line            = line;
        node->if_stmt.cond    = parse_expr(p);
        expect(p, TOK_RPAREN);
        node->if_stmt.then_branch = parse_block(p);
        node->if_stmt.else_branch = NULL;
        if (check(p, TOK_ELSE)) {
            advance(p);
            node->if_stmt.else_branch = parse_block(p);
        }
        return node;
    }

    /* while_stmt */
    if (check(p, TOK_WHILE)) {
        int line = p->current.line;
        advance(p);
        expect(p, TOK_LPAREN);
        ASTNode *node = ast_new(NODE_WHILE);
        node->line              = line;
        node->while_stmt.cond   = parse_expr(p);
        expect(p, TOK_RPAREN);
        node->while_stmt.body   = parse_block(p);
        return node;
    }

    /* return_stmt */
    if (check(p, TOK_RETURN)) {
        int line = p->current.line;
        advance(p);
        ASTNode *node = ast_new(NODE_RETURN);
        node->line = line;
        if (!check(p, TOK_SEMICOLON))
            node->return_stmt.value = parse_expr(p);
        expect(p, TOK_SEMICOLON);
        return node;
    }

    /* Nested block */
    if (check(p, TOK_LBRACE))
        return parse_block(p);

    /* expr_stmt */
    {
        ASTNode *expr = parse_expr(p);
        expect(p, TOK_SEMICOLON);
        ASTNode *node = ast_new(NODE_EXPR_STMT);
        node->line         = expr->line;
        node->expr_stmt.expr = expr;
        return node;
    }
}

/* -----------------------------------------------------------------------
 * Parameter parsing
 * ----------------------------------------------------------------------- */
static ASTNode *parse_param(Parser *p)
{
    /* Optional 'const' qualifier */
    if (check(p, TOK_CONST)) advance(p);

    int is_ptr;
    DataType dt = parse_type(p, &is_ptr);

    ASTNode *node = ast_new(NODE_PARAM);
    node->param.dtype = dt;

    if (check(p, TOK_IDENT)) {
        strncpy(node->param.name, p->current.value, 255);
        node->param.name[255] = '\0';
        advance(p);
    }
    return node;
}

/* -----------------------------------------------------------------------
 * Kernel function parsing
 * ----------------------------------------------------------------------- */
static ASTNode *parse_kernel(Parser *p)
{
    expect(p, TOK_GLOBAL);
    expect(p, TOK_VOID);    /* kernels must return void */

    if (!check(p, TOK_IDENT)) {
        parse_error(p, "expected kernel function name");
        return NULL;
    }
    ASTNode *node = ast_new(NODE_KERNEL_FUNC);
    node->line = p->current.line;
    strncpy(node->kernel_func.name, p->current.value, 255);
    node->kernel_func.name[255] = '\0';
    advance(p);

    expect(p, TOK_LPAREN);
    if (!check(p, TOK_RPAREN)) {
        nodelist_append(&node->kernel_func.params, parse_param(p));
        while (match(p, TOK_COMMA))
            nodelist_append(&node->kernel_func.params, parse_param(p));
    }
    expect(p, TOK_RPAREN);

    node->kernel_func.body = parse_block(p);
    return node;
}

/* -----------------------------------------------------------------------
 * Top-level entry point
 * ----------------------------------------------------------------------- */
ASTNode *parse(Lexer *lex)
{
    Parser p;
    p.lex       = lex;
    p.had_error = 0;
    advance(&p);   /* prime the pump */

    ASTNode *program = ast_new(NODE_PROGRAM);

    while (!check(&p, TOK_EOF)) {
        if (check(&p, TOK_GLOBAL)) {
            ASTNode *kernel = parse_kernel(&p);
            if (kernel)
                nodelist_append(&program->program.kernels, kernel);
        } else {
            /* Skip non-kernel declarations (includes, structs, etc.) */
            advance(&p);
        }
    }

    if (p.had_error)
        fprintf(stderr, "Parsing completed with errors.\n");

    return program;
}
