/*
 * Simple C Compiler - Lexer (Tokenizer) Template
 * 
 * This template guides you through building a lexical analyzer for C.
 * The lexer breaks source code into tokens (keywords, identifiers, operators, etc.)
 * 
 * Compilation: gcc -o lexer lexer.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/*
 * TODO 1: Define token types
 * 
 * Guidelines:
 * - Create an enum for different token types
 * - Include: keywords (int, if, while, return, etc.)
 * - Include: operators (+, -, *, /, ==, !=, etc.)
 * - Include: delimiters ( ; , ( ) { } [ ] )
 * - Include: literals (numbers, strings)
 * - Include: identifiers (variable names)
 */
typedef enum {
    // TODO: Define token types
    TOKEN_INT,      // int keyword
    TOKEN_RETURN,   // return keyword
    TOKEN_IF,       // if keyword
    TOKEN_ELSE,     // else keyword
    TOKEN_WHILE,    // while keyword
    TOKEN_IDENT,    // identifier
    TOKEN_NUMBER,   // number literal
    TOKEN_PLUS,     // +
    TOKEN_MINUS,    // -
    TOKEN_STAR,     // *
    TOKEN_SLASH,    // /
    TOKEN_ASSIGN,   // =
    TOKEN_EQ,       // ==
    TOKEN_NE,       // !=
    TOKEN_LT,       // <
    TOKEN_GT,       // >
    TOKEN_SEMI,     // ;
    TOKEN_LPAREN,   // (
    TOKEN_RPAREN,   // )
    TOKEN_LBRACE,   // {
    TOKEN_RBRACE,   // }
    TOKEN_EOF,      // end of file
    TOKEN_ERROR     // error
} TokenType;

/*
 * TODO 2: Define token structure
 * 
 * Guidelines:
 * - Store token type
 * - Store token value (for numbers and identifiers)
 * - Optionally store position (line, column) for error reporting
 */
typedef struct {
    TokenType type;
    char value[256];
    int line;
    int column;
} Token;

/*
 * TODO 3: Implement is_keyword function
 * 
 * Guidelines:
 * - Check if a string is a C keyword
 * - Return appropriate token type for keywords
 * - Return TOKEN_IDENT for non-keywords
 */
TokenType is_keyword(const char* str) {
    // TODO: Check for keywords
    return TOKEN_IDENT;
}

/*
 * TODO 4: Implement get_next_token function
 * 
 * Guidelines:
 * - Read characters from input
 * - Skip whitespace and comments
 * - Recognize and categorize tokens
 * - Handle multi-character operators (==, !=, etc.)
 * - Build number literals (handle multi-digit numbers)
 * - Build identifiers (alphanumeric + underscore)
 * - Return appropriate token
 */
Token* get_next_token(const char** input, int* line, int* column) {
    // TODO: Implement tokenization
    return NULL;
}

/*
 * TODO 5: Implement tokenize function
 * 
 * Guidelines:
 * - Read entire input and produce list of tokens
 * - Keep calling get_next_token until EOF
 * - Store tokens in an array or linked list
 * - Return the token list
 */
Token** tokenize(const char* input) {
    // TODO: Tokenize entire input
    return NULL;
}

/*
 * Helper function to print tokens
 */
void print_token(Token* token) {
    printf("Token(type=%d, value='%s', line=%d, col=%d)\n", 
           token->type, token->value, token->line, token->column);
}

int main(int argc, char** argv) {
    // Test input
    const char* source = 
        "int main() {\n"
        "    int x = 42;\n"
        "    return x;\n"
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

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Implement is_keyword()
 *         Test with various keywords and identifiers
 * 
 * Step 2: Implement basic get_next_token()
 *         Start with single-character tokens
 *         Test with simple expressions
 * 
 * Step 3: Add number literal recognition
 *         Handle multi-digit numbers
 * 
 * Step 4: Add identifier recognition
 *         Handle variable names
 * 
 * Step 5: Add multi-character operators
 *         Handle ==, !=, <=, >=, etc.
 * 
 * Step 6: Add comment handling
 *         Skip single-line and multi-line comments
 * 
 * Testing Tips:
 * - Test with simple expressions first
 * - Test edge cases (empty input, only whitespace)
 * - Test error cases (invalid characters)
 * - Use printf for debugging
 */
