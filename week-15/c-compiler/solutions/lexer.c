/*
 * Simple C Compiler - Lexer (Tokenizer) Complete Solution
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

typedef enum {
    TOKEN_INT,      
    TOKEN_RETURN,   
    TOKEN_IF,       
    TOKEN_ELSE,     
    TOKEN_WHILE,    
    TOKEN_FOR,
    TOKEN_IDENT,    
    TOKEN_NUMBER,   
    TOKEN_PLUS,     
    TOKEN_MINUS,    
    TOKEN_STAR,     
    TOKEN_SLASH,    
    TOKEN_ASSIGN,   
    TOKEN_EQ,       
    TOKEN_NE,       
    TOKEN_LT,       
    TOKEN_GT,       
    TOKEN_LE,
    TOKEN_GE,
    TOKEN_SEMI,     
    TOKEN_COMMA,
    TOKEN_LPAREN,   
    TOKEN_RPAREN,   
    TOKEN_LBRACE,   
    TOKEN_RBRACE,   
    TOKEN_EOF,      
    TOKEN_ERROR     
} TokenType;

typedef struct {
    TokenType type;
    char value[256];
    int line;
    int column;
} Token;

const char* keywords[] = {"int", "return", "if", "else", "while", "for", NULL};
TokenType keyword_types[] = {TOKEN_INT, TOKEN_RETURN, TOKEN_IF, TOKEN_ELSE, TOKEN_WHILE, TOKEN_FOR};

TokenType is_keyword(const char* str) {
    for (int i = 0; keywords[i] != NULL; i++) {
        if (strcmp(str, keywords[i]) == 0) {
            return keyword_types[i];
        }
    }
    return TOKEN_IDENT;
}

Token* create_token(TokenType type, const char* value, int line, int col) {
    Token* token = malloc(sizeof(Token));
    token->type = type;
    strncpy(token->value, value, sizeof(token->value) - 1);
    token->value[sizeof(token->value) - 1] = '\0';
    token->line = line;
    token->column = col;
    return token;
}

Token* get_next_token(const char** input, int* line, int* column) {
    const char* p = *input;
    
    // Skip whitespace
    while (*p && isspace(*p)) {
        if (*p == '\n') {
            (*line)++;
            *column = 1;
        } else {
            (*column)++;
        }
        p++;
    }
    
    if (*p == '\0') {
        *input = p;
        return create_token(TOKEN_EOF, "", *line, *column);
    }
    
    int start_col = *column;
    
    // Numbers
    if (isdigit(*p)) {
        const char* start = p;
        while (isdigit(*p)) {
            p++;
            (*column)++;
        }
        char num[256];
        int len = p - start;
        strncpy(num, start, len);
        num[len] = '\0';
        *input = p;
        return create_token(TOKEN_NUMBER, num, *line, start_col);
    }
    
    // Identifiers and keywords
    if (isalpha(*p) || *p == '_') {
        const char* start = p;
        while (isalnum(*p) || *p == '_') {
            p++;
            (*column)++;
        }
        char ident[256];
        int len = p - start;
        strncpy(ident, start, len);
        ident[len] = '\0';
        *input = p;
        TokenType type = is_keyword(ident);
        return create_token(type, ident, *line, start_col);
    }
    
    // Operators and delimiters
    char current = *p;
    char next = *(p + 1);
    
    // Two-character operators
    if (current == '=' && next == '=') {
        *input = p + 2;
        *column += 2;
        return create_token(TOKEN_EQ, "==", *line, start_col);
    }
    if (current == '!' && next == '=') {
        *input = p + 2;
        *column += 2;
        return create_token(TOKEN_NE, "!=", *line, start_col);
    }
    if (current == '<' && next == '=') {
        *input = p + 2;
        *column += 2;
        return create_token(TOKEN_LE, "<=", *line, start_col);
    }
    if (current == '>' && next == '=') {
        *input = p + 2;
        *column += 2;
        return create_token(TOKEN_GE, ">=", *line, start_col);
    }
    
    // Single-character tokens
    TokenType type = TOKEN_ERROR;
    char value[2] = {current, '\0'};
    
    switch (current) {
        case '+': type = TOKEN_PLUS; break;
        case '-': type = TOKEN_MINUS; break;
        case '*': type = TOKEN_STAR; break;
        case '/': type = TOKEN_SLASH; break;
        case '=': type = TOKEN_ASSIGN; break;
        case '<': type = TOKEN_LT; break;
        case '>': type = TOKEN_GT; break;
        case ';': type = TOKEN_SEMI; break;
        case ',': type = TOKEN_COMMA; break;
        case '(': type = TOKEN_LPAREN; break;
        case ')': type = TOKEN_RPAREN; break;
        case '{': type = TOKEN_LBRACE; break;
        case '}': type = TOKEN_RBRACE; break;
        default: type = TOKEN_ERROR; break;
    }
    
    *input = p + 1;
    (*column)++;
    return create_token(type, value, *line, start_col);
}

Token** tokenize(const char* input) {
    int capacity = 100;
    Token** tokens = malloc(capacity * sizeof(Token*));
    int count = 0;
    
    int line = 1, column = 1;
    const char* p = input;
    
    while (*p) {
        Token* token = get_next_token(&p, &line, &column);
        
        if (count >= capacity - 1) {
            capacity *= 2;
            tokens = realloc(tokens, capacity * sizeof(Token*));
        }
        
        tokens[count++] = token;
        
        if (token->type == TOKEN_EOF) {
            break;
        }
    }
    
    tokens[count] = NULL;
    return tokens;
}

void print_token(Token* token) {
    const char* type_names[] = {
        "INT", "RETURN", "IF", "ELSE", "WHILE", "FOR", "IDENT", "NUMBER",
        "PLUS", "MINUS", "STAR", "SLASH", "ASSIGN", "EQ", "NE", "LT", "GT",
        "LE", "GE", "SEMI", "COMMA", "LPAREN", "RPAREN", "LBRACE", "RBRACE",
        "EOF", "ERROR"
    };
    printf("%-10s '%s' (line %d, col %d)\n", 
           type_names[token->type], token->value, token->line, token->column);
}

int main() {
    const char* source = 
        "int main() {\n"
        "    int x = 42;\n"
        "    if (x >= 10) {\n"
        "        return x;\n"
        "    }\n"
        "    return 0;\n"
        "}\n";
    
    printf("Source code:\n%s\n", source);
    printf("Tokens:\n");
    
    Token** tokens = tokenize(source);
    
    if (tokens) {
        for (int i = 0; tokens[i] != NULL; i++) {
            print_token(tokens[i]);
            free(tokens[i]);
        }
        free(tokens);
    }
    
    return 0;
}
