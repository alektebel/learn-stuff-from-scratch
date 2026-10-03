/*
 * Simple C Compiler - Parser Implementation Template
 * 
 * This template guides you through building a recursive descent parser for C.
 * The parser takes tokens from the lexer and builds an Abstract Syntax Tree (AST).
 * 
 * A recursive descent parser uses a set of recursive functions, one for each
 * grammar rule, to parse the input tokens.
 * 
 * Compilation: gcc -o parser parser.c lexer.c -I.
 * 
 * GRAMMAR (Simplified C Subset):
 * 
 * program       → function*
 * function      → type IDENT '(' params? ')' compound
 * params        → param (',' param)*
 * param         → type IDENT
 * 
 * compound      → '{' statement* '}'
 * statement     → declaration
 *               | return_stmt
 *               | if_stmt
 *               | while_stmt
 *               | for_stmt
 *               | expr_stmt
 *               | compound
 * 
 * declaration   → type IDENT ('=' expr)? ';'
 * return_stmt   → 'return' expr ';'
 * if_stmt       → 'if' '(' expr ')' statement ('else' statement)?
 * while_stmt    → 'while' '(' expr ')' statement
 * for_stmt      → 'for' '(' expr? ';' expr? ';' expr? ')' statement
 * expr_stmt     → expr ';'
 * 
 * expr          → assignment
 * assignment    → logical_or ('=' assignment)?
 * logical_or    → logical_and ('||' logical_and)*
 * logical_and   → equality ('&&' equality)*
 * equality      → relational (('==' | '!=') relational)*
 * relational    → additive (('<' | '>' | '<=' | '>=') additive)*
 * additive      → multiplicative (('+' | '-') multiplicative)*
 * multiplicative → unary (('*' | '/') unary)*
 * unary         → ('+' | '-' | '!' | '&' | '*') unary
 *               | postfix
 * postfix       → primary ('[' expr ']' | '(' args? ')')*
 * primary       → IDENT
 *               | NUMBER
 *               | STRING
 *               | '(' expr ')'
 * 
 * args          → expr (',' expr)*
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "ast.h"

/*
 * Assume we have a lexer that provides these token definitions.
 * In a real implementation, include the lexer header file.
 */
typedef enum {
    TOKEN_INT, TOKEN_CHAR, TOKEN_VOID,
    TOKEN_RETURN, TOKEN_IF, TOKEN_ELSE, TOKEN_WHILE, TOKEN_FOR,
    TOKEN_IDENT, TOKEN_NUMBER, TOKEN_STRING,
    TOKEN_PLUS, TOKEN_MINUS, TOKEN_STAR, TOKEN_SLASH, TOKEN_MOD,
    TOKEN_ASSIGN, TOKEN_EQ, TOKEN_NE, TOKEN_LT, TOKEN_GT, TOKEN_LE, TOKEN_GE,
    TOKEN_AND, TOKEN_OR, TOKEN_NOT,
    TOKEN_AMPERSAND, TOKEN_SEMI, TOKEN_COMMA,
    TOKEN_LPAREN, TOKEN_RPAREN, TOKEN_LBRACE, TOKEN_RBRACE,
    TOKEN_LBRACKET, TOKEN_RBRACKET,
    TOKEN_EOF, TOKEN_ERROR
} TokenType;

typedef struct {
    TokenType type;
    char value[256];
    int line;
    int column;
} Token;

/*
 * Parser State
 * 
 * The parser maintains state about the current token and the token list.
 */
typedef struct {
    Token** tokens;         // Array of tokens from lexer
    int current;            // Current token index
    int error_count;        // Number of parse errors encountered
} Parser;

/*
 * TODO 1: Implement parser initialization
 * 
 * Guidelines:
 * - Initialize parser with token array from lexer
 * - Set current position to 0
 * - Initialize error count to 0
 */
Parser* create_parser(Token** tokens) {
    // TODO: Allocate and initialize Parser struct
    Parser* parser = malloc(sizeof(Parser));
    parser->tokens = tokens;
    parser->current = 0;
    parser->error_count = 0;
    return parser;
}

/*
 * TODO 2: Implement token access functions
 * 
 * Guidelines:
 * - peek(): Return current token without advancing
 * - previous(): Return previous token
 * - is_at_end(): Check if we've reached EOF token
 * - advance(): Move to next token and return previous
 * - check(): Check if current token matches a type
 * - match(): Check and consume if token matches
 */

// Return current token without consuming it
Token* peek(Parser* parser) {
    // TODO: Return current token
    return NULL;
}

// Return previous token
Token* previous(Parser* parser) {
    // TODO: Return token at current - 1
    return NULL;
}

// Check if we're at end of token stream
bool is_at_end(Parser* parser) {
    // TODO: Check if current token is TOKEN_EOF
    return false;
}

// Consume and return current token
Token* advance(Parser* parser) {
    // TODO: Move to next token and return previous one
    return NULL;
}

// Check if current token matches given type
bool check(Parser* parser, TokenType type) {
    // TODO: Check token type without consuming
    return false;
}

// If current token matches type, consume it and return true
bool match(Parser* parser, TokenType type) {
    // TODO: Check and advance if match
    return false;
}

// If current token matches any of multiple types, consume and return true
bool match_any(Parser* parser, int count, ...) {
    // TODO: Check against multiple token types using varargs
    return false;
}

/*
 * TODO 3: Implement error handling
 * 
 * Guidelines:
 * - Report parse errors with line/column information
 * - Attempt error recovery (synchronization)
 * - Keep track of error count
 */

void parser_error(Parser* parser, const char* message) {
    Token* token = peek(parser);
    fprintf(stderr, "Parse error at line %d, column %d: %s\n",
            token->line, token->column, message);
    parser->error_count++;
}

// Expect a specific token type, consume it, or report error
Token* expect(Parser* parser, TokenType type, const char* message) {
    if (check(parser, type)) {
        return advance(parser);
    }
    parser_error(parser, message);
    return NULL;
}

// Error recovery: skip tokens until we find a synchronization point
void synchronize(Parser* parser) {
    advance(parser);
    
    while (!is_at_end(parser)) {
        if (previous(parser)->type == TOKEN_SEMI) return;
        
        switch (peek(parser)->type) {
            case TOKEN_INT:
            case TOKEN_RETURN:
            case TOKEN_IF:
            case TOKEN_WHILE:
            case TOKEN_FOR:
                return;
            default:
                break;
        }
        
        advance(parser);
    }
}

/*
 * TODO 4: Implement type parsing
 * 
 * Guidelines:
 * - Parse type keywords (int, char, void)
 * - Handle pointer types (int*, char**, etc.)
 * - Return TypeInfo structure
 */
TypeInfo* parse_type(Parser* parser) {
    // TODO: Parse type specifiers
    // Example: int, int*, char, void
    return NULL;
}

/*
 * TODO 5: Implement expression parsing
 * 
 * Guidelines:
 * - Implement operator precedence using recursive descent
 * - Each precedence level has its own function
 * - Higher precedence = deeper in recursion
 * - Left-associative operators use loops
 * - Right-associative operators use recursion
 * 
 * Precedence (high to low):
 * 1. primary (identifiers, literals, parentheses)
 * 2. postfix (function calls, array subscripts)
 * 3. unary (-, !, &, *)
 * 4. multiplicative (*, /)
 * 5. additive (+, -)
 * 6. relational (<, >, <=, >=)
 * 7. equality (==, !=)
 * 8. logical AND (&&)
 * 9. logical OR (||)
 * 10. assignment (=) - right associative
 */

// Forward declarations for parsing functions
ASTNode* parse_primary(Parser* parser);
ASTNode* parse_postfix(Parser* parser);
ASTNode* parse_unary(Parser* parser);
ASTNode* parse_multiplicative(Parser* parser);
ASTNode* parse_additive(Parser* parser);
ASTNode* parse_relational(Parser* parser);
ASTNode* parse_equality(Parser* parser);
ASTNode* parse_logical_and(Parser* parser);
ASTNode* parse_logical_or(Parser* parser);
ASTNode* parse_assignment(Parser* parser);
ASTNode* parse_expression(Parser* parser);

// Primary expressions: identifiers, numbers, strings, parenthesized expressions
ASTNode* parse_primary(Parser* parser) {
    // TODO: Implement primary expression parsing
    // - NUMBER: create literal node
    // - IDENT: create identifier node  
    // - '(' expr ')': parse nested expression
    return NULL;
}

// Postfix expressions: function calls, array subscripts
ASTNode* parse_postfix(Parser* parser) {
    // TODO: Implement postfix expression parsing
    // Start with primary, then handle '(' for calls, '[' for subscripts
    ASTNode* expr = parse_primary(parser);
    
    // TODO: Loop to handle multiple postfix operators
    // - '(' args ')': function call
    // - '[' expr ']': array subscript
    
    return expr;
}

// Unary expressions: -, !, &, *
ASTNode* parse_unary(Parser* parser) {
    // TODO: Implement unary expression parsing
    // If we see unary operator, create unary node with recursive call
    // Otherwise, call parse_postfix
    return NULL;
}

// Multiplicative expressions: *, /, %
ASTNode* parse_multiplicative(Parser* parser) {
    // TODO: Implement multiplicative expression parsing
    // Left-associative: use loop
    // Start with parse_unary, then loop for operators
    return NULL;
}

// Additive expressions: +, -
ASTNode* parse_additive(Parser* parser) {
    // TODO: Implement additive expression parsing
    // Left-associative: use loop
    // Start with parse_multiplicative, then loop for operators
    return NULL;
}

// Relational expressions: <, >, <=, >=
ASTNode* parse_relational(Parser* parser) {
    // TODO: Implement relational expression parsing
    return NULL;
}

// Equality expressions: ==, !=
ASTNode* parse_equality(Parser* parser) {
    // TODO: Implement equality expression parsing
    return NULL;
}

// Logical AND expressions: &&
ASTNode* parse_logical_and(Parser* parser) {
    // TODO: Implement logical AND parsing
    return NULL;
}

// Logical OR expressions: ||
ASTNode* parse_logical_or(Parser* parser) {
    // TODO: Implement logical OR parsing
    return NULL;
}

// Assignment expressions: =
ASTNode* parse_assignment(Parser* parser) {
    // TODO: Implement assignment parsing
    // Right-associative: use recursion
    // Parse left side, check for '=', then recurse for right side
    return NULL;
}

// Top-level expression parser
ASTNode* parse_expression(Parser* parser) {
    return parse_assignment(parser);
}

/*
 * TODO 6: Implement statement parsing
 * 
 * Guidelines:
 * - Each statement type has its own parsing function
 * - Look at first token to determine statement type
 * - Handle compound statements (blocks)
 * - Parse control flow statements (if, while, for)
 */

ASTNode* parse_statement(Parser* parser);

// Parse variable declaration: type IDENT ('=' expr)? ';'
ASTNode* parse_declaration(Parser* parser) {
    // TODO: Implement declaration parsing
    // 1. Parse type
    // 2. Expect identifier
    // 3. Check for '=' and parse initializer if present
    // 4. Expect ';'
    return NULL;
}

// Parse return statement: 'return' expr ';'
ASTNode* parse_return(Parser* parser) {
    // TODO: Implement return statement parsing
    return NULL;
}

// Parse if statement: 'if' '(' expr ')' stmt ('else' stmt)?
ASTNode* parse_if(Parser* parser) {
    // TODO: Implement if statement parsing
    return NULL;
}

// Parse while statement: 'while' '(' expr ')' stmt
ASTNode* parse_while(Parser* parser) {
    // TODO: Implement while statement parsing
    return NULL;
}

// Parse for statement: 'for' '(' expr? ';' expr? ';' expr? ')' stmt
ASTNode* parse_for(Parser* parser) {
    // TODO: Implement for statement parsing
    return NULL;
}

// Parse compound statement: '{' stmt* '}'
ASTNode* parse_compound(Parser* parser) {
    // TODO: Implement compound statement parsing
    // 1. Expect '{'
    // 2. Loop parsing statements until '}'
    // 3. Build list of statements
    // 4. Expect '}'
    return NULL;
}

// Parse expression statement: expr ';'
ASTNode* parse_expr_stmt(Parser* parser) {
    // TODO: Implement expression statement parsing
    return NULL;
}

// Parse any statement (dispatch to specific parser based on first token)
ASTNode* parse_statement(Parser* parser) {
    // TODO: Look at current token and dispatch to appropriate parser
    // - '{' → compound
    // - 'return' → return statement
    // - 'if' → if statement
    // - 'while' → while statement
    // - 'for' → for statement
    // - type keyword → declaration
    // - otherwise → expression statement
    return NULL;
}

/*
 * TODO 7: Implement function and program parsing
 * 
 * Guidelines:
 * - Parse function definitions
 * - Parse parameter lists
 * - Parse entire program (list of functions)
 */

// Parse function parameter: type IDENT
ASTNode* parse_parameter(Parser* parser) {
    // TODO: Implement parameter parsing
    return NULL;
}

// Parse parameter list: param (',' param)*
ASTNode* parse_parameters(Parser* parser) {
    // TODO: Implement parameter list parsing
    // Build linked list of parameters using 'next' pointer
    return NULL;
}

// Parse function: type IDENT '(' params? ')' compound
ASTNode* parse_function(Parser* parser) {
    // TODO: Implement function parsing
    // 1. Parse return type
    // 2. Parse function name
    // 3. Expect '('
    // 4. Parse parameters
    // 5. Expect ')'
    // 6. Parse compound statement (body)
    return NULL;
}

// Parse program: function*
ASTNode* parse_program(Parser* parser) {
    // TODO: Implement program parsing
    // Keep parsing functions until EOF
    // Build linked list of functions
    return NULL;
}

/*
 * Main parsing entry point
 */
ASTNode* parse(Token** tokens) {
    Parser* parser = create_parser(tokens);
    ASTNode* ast = parse_program(parser);
    
    if (parser->error_count > 0) {
        fprintf(stderr, "Parsing failed with %d error(s)\n", 
                parser->error_count);
        free_ast(ast);
        free(parser);
        return NULL;
    }
    
    free(parser);
    return ast;
}

/*
 * Test main (for standalone testing)
 */
int main(int argc, char** argv) {
    // Example usage (requires lexer implementation)
    printf("Parser template - implement the TODO sections\n");
    printf("This parser will build an AST from tokens\n");
    
    // TODO: Integrate with lexer
    // Token** tokens = tokenize(source_code);
    // ASTNode* ast = parse(tokens);
    // print_ast(ast, 0);
    // free_ast(ast);
    
    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Implement token access functions (peek, advance, check, match)
 *         Test with simple token sequences
 * 
 * Step 2: Implement primary expression parsing
 *         Test: 42, x, (10 + 20)
 * 
 * Step 3: Implement unary expression parsing
 *         Test: -x, !flag, &var
 * 
 * Step 4: Implement binary expression parsing (one precedence level at a time)
 *         Test: 2 + 3, 5 * 6, 10 == 10
 * 
 * Step 5: Implement statement parsing (one type at a time)
 *         Test: return 0; x = 5; if (x > 0) return 1;
 * 
 * Step 6: Implement function parsing
 *         Test: int main() { return 0; }
 * 
 * Step 7: Implement program parsing (multiple functions)
 *         Test full programs
 * 
 * Testing Strategy:
 * - Start with minimal valid programs
 * - Add complexity incrementally
 * - Test error cases (missing semicolons, mismatched parentheses)
 * - Use print_ast to visualize parsed structure
 * - Compare AST structure with expected parse tree
 * 
 * Debugging Tips:
 * - Print current token in each parsing function
 * - Use print_ast to visualize partial ASTs
 * - Add assertions to check invariants
 * - Test each grammar rule in isolation
 * - Use a debugger to step through recursive calls
 * 
 * Common Pitfalls:
 * - Forgetting to advance() after checking token
 * - Incorrect operator precedence
 * - Not handling empty productions (e.g., empty parameter list)
 * - Memory leaks from not freeing AST nodes on errors
 * - Not synchronizing after parse errors
 */
