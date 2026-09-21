/*
 * Tiny CUDA Compiler - Lexer (Tokenizer)
 *
 * Breaks a CUDA source file into a stream of tokens.
 * Handles all CUDA-specific keywords (__global__, threadIdx, etc.)
 * in addition to standard C tokens.
 */

#ifndef CUDA_LEXER_H
#define CUDA_LEXER_H

/* -----------------------------------------------------------------------
 * Token types
 * ----------------------------------------------------------------------- */
typedef enum {
    /* CUDA qualifiers */
    TOK_GLOBAL,         /* __global__  */
    TOK_DEVICE,         /* __device__  */
    TOK_SHARED,         /* __shared__  */
    TOK_CONSTANT,       /* __constant__ */

    /* C types */
    TOK_VOID,
    TOK_INT,
    TOK_FLOAT,
    TOK_UNSIGNED,
    TOK_CONST,

    /* Control flow */
    TOK_IF,
    TOK_ELSE,
    TOK_FOR,
    TOK_WHILE,
    TOK_RETURN,

    /* CUDA built-in variables */
    TOK_THREADIDX,      /* threadIdx */
    TOK_BLOCKIDX,       /* blockIdx  */
    TOK_BLOCKDIM,       /* blockDim  */
    TOK_GRIDDIM,        /* gridDim   */

    /* Dimension selectors (consumed with the preceding dot) */
    TOK_DOT_X,          /* .x */
    TOK_DOT_Y,          /* .y */
    TOK_DOT_Z,          /* .z */

    /* Identifiers and literals */
    TOK_IDENT,
    TOK_INT_LIT,
    TOK_FLOAT_LIT,

    /* Operators */
    TOK_PLUS,           /* +  */
    TOK_MINUS,          /* -  */
    TOK_STAR,           /* *  */
    TOK_SLASH,          /* /  */
    TOK_PERCENT,        /* %  */
    TOK_ASSIGN,         /* =  */
    TOK_EQ,             /* == */
    TOK_NE,             /* != */
    TOK_LT,             /* <  */
    TOK_GT,             /* >  */
    TOK_LE,             /* <= */
    TOK_GE,             /* >= */
    TOK_AND,            /* && */
    TOK_OR,             /* || */
    TOK_NOT,            /* !  */
    TOK_AMP,            /* &  */
    TOK_PIPE,           /* |  */

    /* Punctuation */
    TOK_LPAREN,         /* ( */
    TOK_RPAREN,         /* ) */
    TOK_LBRACE,         /* { */
    TOK_RBRACE,         /* } */
    TOK_LBRACKET,       /* [ */
    TOK_RBRACKET,       /* ] */
    TOK_SEMICOLON,      /* ; */
    TOK_COMMA,          /* , */
    TOK_DOT,            /* . */

    /* Special */
    TOK_EOF,
    TOK_ERROR
} TokenType;

/* -----------------------------------------------------------------------
 * Token
 * ----------------------------------------------------------------------- */
typedef struct {
    TokenType   type;
    char        value[256]; /* token text (identifier name, literal, etc.) */
    int         line;
    int         col;
} Token;

/* -----------------------------------------------------------------------
 * Lexer state
 * ----------------------------------------------------------------------- */
typedef struct {
    const char *src;        /* NUL-terminated source text  */
    int         pos;        /* current read position       */
    int         line;       /* current line (1-based)      */
    int         col;        /* current column (1-based)    */
    Token       lookahead;  /* one-token lookahead buffer  */
    int         has_lookahead;
} Lexer;

/* -----------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */
void        lexer_init      (Lexer *lex, const char *source);
Token       lexer_next      (Lexer *lex);   /* consume and return next token */
Token       lexer_peek      (Lexer *lex);   /* peek without consuming        */
const char *token_type_name (TokenType t);

#endif /* CUDA_LEXER_H */
