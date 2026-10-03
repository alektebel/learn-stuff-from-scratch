/*
 * Tiny CUDA Compiler - Lexer Implementation
 *
 * Scans a CUDA source string and produces tokens one at a time.
 *
 * Compile:  (included via Makefile - not compiled standalone)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "lexer.h"

/* -----------------------------------------------------------------------
 * Keyword table
 * ----------------------------------------------------------------------- */
static const struct { const char *word; TokenType type; } KEYWORDS[] = {
    { "__global__",   TOK_GLOBAL   },
    { "__device__",   TOK_DEVICE   },
    { "__shared__",   TOK_SHARED   },
    { "__constant__", TOK_CONSTANT },
    { "void",         TOK_VOID     },
    { "int",          TOK_INT      },
    { "float",        TOK_FLOAT    },
    { "unsigned",     TOK_UNSIGNED },
    { "const",        TOK_CONST    },
    { "if",           TOK_IF       },
    { "else",         TOK_ELSE     },
    { "for",          TOK_FOR      },
    { "while",        TOK_WHILE    },
    { "return",       TOK_RETURN   },
    { "threadIdx",    TOK_THREADIDX },
    { "blockIdx",     TOK_BLOCKIDX  },
    { "blockDim",     TOK_BLOCKDIM  },
    { "gridDim",      TOK_GRIDDIM   },
    { NULL,           TOK_EOF      }   /* sentinel */
};

static TokenType classify_ident(const char *s)
{
    for (int i = 0; KEYWORDS[i].word; i++)
        if (strcmp(s, KEYWORDS[i].word) == 0)
            return KEYWORDS[i].type;
    return TOK_IDENT;
}

/* -----------------------------------------------------------------------
 * Lexer internals
 * ----------------------------------------------------------------------- */
void lexer_init(Lexer *lex, const char *source)
{
    lex->src          = source;
    lex->pos          = 0;
    lex->line         = 1;
    lex->col          = 1;
    lex->has_lookahead = 0;
}

static char cur(const Lexer *lex)  { return lex->src[lex->pos]; }
static char nxt(const Lexer *lex)  { return lex->src[lex->pos + 1]; }

static char advance(Lexer *lex)
{
    char c = lex->src[lex->pos++];
    if (c == '\n') { lex->line++; lex->col = 1; }
    else            { lex->col++; }
    return c;
}

static void skip_whitespace_and_comments(Lexer *lex)
{
    while (1) {
        /* Whitespace */
        while (isspace((unsigned char)cur(lex)))
            advance(lex);

        /* C++ single-line comment: // ... */
        if (cur(lex) == '/' && nxt(lex) == '/') {
            while (cur(lex) && cur(lex) != '\n')
                advance(lex);
            continue;
        }

        /* C block comment: slash-star ... star-slash */
        if (cur(lex) == '/' && nxt(lex) == '*') {
            advance(lex); advance(lex);
            while (cur(lex)) {
                if (cur(lex) == '*' && nxt(lex) == '/') {
                    advance(lex); advance(lex);
                    break;
                }
                advance(lex);
            }
            continue;
        }

        /* Preprocessor lines (#include, #define, ...) */
        if (cur(lex) == '#') {
            while (cur(lex) && cur(lex) != '\n')
                advance(lex);
            continue;
        }

        break;
    }
}

/* -----------------------------------------------------------------------
 * lexer_next – produce the next token from the source stream
 * ----------------------------------------------------------------------- */
Token lexer_next(Lexer *lex)
{
    /* Return buffered lookahead if present */
    if (lex->has_lookahead) {
        lex->has_lookahead = 0;
        return lex->lookahead;
    }

    skip_whitespace_and_comments(lex);

    Token tok;
    tok.line     = lex->line;
    tok.col      = lex->col;
    tok.value[0] = '\0';

    char c = cur(lex);

    /* EOF */
    if (c == '\0') {
        tok.type = TOK_EOF;
        strcpy(tok.value, "EOF");
        return tok;
    }

    /* Identifier or keyword (including __global__ etc.) */
    if (isalpha((unsigned char)c) || c == '_') {
        int i = 0;
        while (isalnum((unsigned char)cur(lex)) || cur(lex) == '_')
            tok.value[i++] = advance(lex);
        tok.value[i] = '\0';
        tok.type = classify_ident(tok.value);
        return tok;
    }

    /* Numeric literal (integer or float) */
    if (isdigit((unsigned char)c)) {
        int i = 0, is_float = 0;
        while (isdigit((unsigned char)cur(lex)))
            tok.value[i++] = advance(lex);
        if (cur(lex) == '.') {
            is_float = 1;
            tok.value[i++] = advance(lex);
            while (isdigit((unsigned char)cur(lex)))
                tok.value[i++] = advance(lex);
        }
        /* Optional 'f' suffix */
        if (cur(lex) == 'f' || cur(lex) == 'F') {
            is_float = 1;
            advance(lex);
        }
        tok.value[i] = '\0';
        tok.type = is_float ? TOK_FLOAT_LIT : TOK_INT_LIT;
        return tok;
    }

    /* Consume the character */
    advance(lex);
    tok.value[0] = c;
    tok.value[1] = '\0';

    switch (c) {
        case '+': tok.type = TOK_PLUS;      break;
        case '-': tok.type = TOK_MINUS;     break;
        case '*': tok.type = TOK_STAR;      break;
        case '/': tok.type = TOK_SLASH;     break;
        case '%': tok.type = TOK_PERCENT;   break;
        case '(': tok.type = TOK_LPAREN;    break;
        case ')': tok.type = TOK_RPAREN;    break;
        case '{': tok.type = TOK_LBRACE;    break;
        case '}': tok.type = TOK_RBRACE;    break;
        case '[': tok.type = TOK_LBRACKET;  break;
        case ']': tok.type = TOK_RBRACKET;  break;
        case ';': tok.type = TOK_SEMICOLON; break;
        case ',': tok.type = TOK_COMMA;     break;

        case '!':
            if (cur(lex) == '=') {
                advance(lex);
                tok.type = TOK_NE;
                strcpy(tok.value, "!=");
            } else {
                tok.type = TOK_NOT;
            }
            break;

        case '<':
            if (cur(lex) == '=') {
                advance(lex);
                tok.type = TOK_LE;
                strcpy(tok.value, "<=");
            } else {
                tok.type = TOK_LT;
            }
            break;

        case '>':
            if (cur(lex) == '=') {
                advance(lex);
                tok.type = TOK_GE;
                strcpy(tok.value, ">=");
            } else {
                tok.type = TOK_GT;
            }
            break;

        case '=':
            if (cur(lex) == '=') {
                advance(lex);
                tok.type = TOK_EQ;
                strcpy(tok.value, "==");
            } else {
                tok.type = TOK_ASSIGN;
            }
            break;

        case '&':
            if (cur(lex) == '&') {
                advance(lex);
                tok.type = TOK_AND;
                strcpy(tok.value, "&&");
            } else {
                tok.type = TOK_AMP;
            }
            break;

        case '|':
            if (cur(lex) == '|') {
                advance(lex);
                tok.type = TOK_OR;
                strcpy(tok.value, "||");
            } else {
                tok.type = TOK_PIPE;
            }
            break;

        case '.':
            /*
             * Dimension selectors: .x, .y, .z
             * Only treat as dimension if the next char is x/y/z followed
             * by a non-alphanumeric character (so ".xyz" stays as ident).
             */
            if (cur(lex) == 'x' && !isalnum((unsigned char)nxt(lex)) && nxt(lex) != '_') {
                advance(lex);
                tok.type = TOK_DOT_X;
                strcpy(tok.value, ".x");
            } else if (cur(lex) == 'y' && !isalnum((unsigned char)nxt(lex)) && nxt(lex) != '_') {
                advance(lex);
                tok.type = TOK_DOT_Y;
                strcpy(tok.value, ".y");
            } else if (cur(lex) == 'z' && !isalnum((unsigned char)nxt(lex)) && nxt(lex) != '_') {
                advance(lex);
                tok.type = TOK_DOT_Z;
                strcpy(tok.value, ".z");
            } else {
                tok.type = TOK_DOT;
            }
            break;

        default:
            tok.type = TOK_ERROR;
            break;
    }

    return tok;
}

/* -----------------------------------------------------------------------
 * lexer_peek – return next token without consuming it
 * ----------------------------------------------------------------------- */
Token lexer_peek(Lexer *lex)
{
    if (!lex->has_lookahead) {
        lex->lookahead     = lexer_next(lex);
        lex->has_lookahead = 1;
    }
    return lex->lookahead;
}

/* -----------------------------------------------------------------------
 * token_type_name – human-readable token type string (for diagnostics)
 * ----------------------------------------------------------------------- */
const char *token_type_name(TokenType t)
{
    switch (t) {
        case TOK_GLOBAL:    return "__global__";
        case TOK_DEVICE:    return "__device__";
        case TOK_SHARED:    return "__shared__";
        case TOK_CONSTANT:  return "__constant__";
        case TOK_VOID:      return "void";
        case TOK_INT:       return "int";
        case TOK_FLOAT:     return "float";
        case TOK_UNSIGNED:  return "unsigned";
        case TOK_CONST:     return "const";
        case TOK_IF:        return "if";
        case TOK_ELSE:      return "else";
        case TOK_FOR:       return "for";
        case TOK_WHILE:     return "while";
        case TOK_RETURN:    return "return";
        case TOK_THREADIDX: return "threadIdx";
        case TOK_BLOCKIDX:  return "blockIdx";
        case TOK_BLOCKDIM:  return "blockDim";
        case TOK_GRIDDIM:   return "gridDim";
        case TOK_DOT_X:     return ".x";
        case TOK_DOT_Y:     return ".y";
        case TOK_DOT_Z:     return ".z";
        case TOK_IDENT:     return "identifier";
        case TOK_INT_LIT:   return "int_literal";
        case TOK_FLOAT_LIT: return "float_literal";
        case TOK_PLUS:      return "+";
        case TOK_MINUS:     return "-";
        case TOK_STAR:      return "*";
        case TOK_SLASH:     return "/";
        case TOK_PERCENT:   return "%";
        case TOK_ASSIGN:    return "=";
        case TOK_EQ:        return "==";
        case TOK_NE:        return "!=";
        case TOK_LT:        return "<";
        case TOK_GT:        return ">";
        case TOK_LE:        return "<=";
        case TOK_GE:        return ">=";
        case TOK_AND:       return "&&";
        case TOK_OR:        return "||";
        case TOK_NOT:       return "!";
        case TOK_AMP:       return "&";
        case TOK_PIPE:      return "|";
        case TOK_LPAREN:    return "(";
        case TOK_RPAREN:    return ")";
        case TOK_LBRACE:    return "{";
        case TOK_RBRACE:    return "}";
        case TOK_LBRACKET:  return "[";
        case TOK_RBRACKET:  return "]";
        case TOK_SEMICOLON: return ";";
        case TOK_COMMA:     return ",";
        case TOK_DOT:       return ".";
        case TOK_EOF:       return "EOF";
        case TOK_ERROR:     return "ERROR";
        default:            return "UNKNOWN";
    }
}
