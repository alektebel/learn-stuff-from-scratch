/*
 * Simple C Compiler - Semantic Analyzer Template
 * 
 * This template guides you through building a semantic analyzer for C.
 * The semantic analyzer performs type checking, validates declarations,
 * and ensures the program follows C's semantic rules.
 * 
 * Semantic analysis phase:
 * 1. Symbol table construction (track variables, functions)
 * 2. Type checking (ensure operations are type-correct)
 * 3. Scope management (nested scopes for blocks)
 * 4. Declaration/usage validation (variables used before declaration)
 * 5. Function call validation (correct number and types of arguments)
 * 
 * Compilation: gcc -o semantic semantic.c parser.c lexer.c -I.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "ast.h"

/*
 * Symbol Table Entry
 * 
 * Represents a symbol (variable or function) in the symbol table.
 * Stores name, type information, and scope level.
 */
typedef struct Symbol {
    char* name;
    TypeInfo* type;
    int scope_level;
    bool is_function;
    int param_count;        // For functions
    struct Symbol* next;    // For chaining in hash table
} Symbol;

/*
 * Symbol Table
 * 
 * Hash table for fast symbol lookup.
 * Each scope has its own symbol table linked to parent scope.
 */
#define SYMBOL_TABLE_SIZE 256

typedef struct SymbolTable {
    Symbol* buckets[SYMBOL_TABLE_SIZE];
    struct SymbolTable* parent;     // Parent scope
    int scope_level;
} SymbolTable;

/*
 * Semantic Analyzer State
 * 
 * Maintains state during semantic analysis including:
 * - Current symbol table (changes as we enter/exit scopes)
 * - Global symbol table
 * - Current function being analyzed
 * - Error count
 */
typedef struct {
    SymbolTable* current_scope;
    SymbolTable* global_scope;
    Symbol* current_function;
    int error_count;
    int scope_level;
} SemanticAnalyzer;

/*
 * TODO 1: Implement symbol table operations
 * 
 * Guidelines:
 * - Hash function for symbol table
 * - Create and destroy symbol tables
 * - Enter and exit scopes
 * - Insert and lookup symbols
 * - Handle shadowing (inner scope hides outer scope)
 */

// Simple hash function for symbol names
unsigned int hash_symbol(const char* name) {
    // TODO: Implement hash function (e.g., djb2 algorithm)
    unsigned int hash = 5381;
    int c;
    while ((c = *name++)) {
        hash = ((hash << 5) + hash) + c; // hash * 33 + c
    }
    return hash % SYMBOL_TABLE_SIZE;
}

// Create new symbol table
SymbolTable* create_symbol_table(SymbolTable* parent, int scope_level) {
    // TODO: Allocate and initialize symbol table
    SymbolTable* table = malloc(sizeof(SymbolTable));
    for (int i = 0; i < SYMBOL_TABLE_SIZE; i++) {
        table->buckets[i] = NULL;
    }
    table->parent = parent;
    table->scope_level = scope_level;
    return table;
}

// Free symbol table and all symbols
void free_symbol_table(SymbolTable* table) {
    // TODO: Free all symbols and the table itself
    if (!table) return;
    
    for (int i = 0; i < SYMBOL_TABLE_SIZE; i++) {
        Symbol* sym = table->buckets[i];
        while (sym) {
            Symbol* next = sym->next;
            free(sym->name);
            free_type_info(sym->type);
            free(sym);
            sym = next;
        }
    }
    free(table);
}

// Insert symbol into symbol table
bool insert_symbol(SymbolTable* table, const char* name, TypeInfo* type, 
                   bool is_function, int param_count) {
    // TODO: Create new symbol and insert into table
    // Check for duplicate declarations in same scope
    // Return false if symbol already exists in current scope
    return true;
}

// Look up symbol in current and parent scopes
Symbol* lookup_symbol(SymbolTable* table, const char* name) {
    // TODO: Search current scope and parent scopes
    // Walk up scope chain until symbol found or global scope reached
    return NULL;
}

// Look up symbol only in current scope (for duplicate checking)
Symbol* lookup_symbol_current_scope(SymbolTable* table, const char* name) {
    // TODO: Search only in current scope
    return NULL;
}

/*
 * TODO 2: Implement semantic analyzer initialization
 * 
 * Guidelines:
 * - Create global symbol table
 * - Set up initial scope
 * - Initialize error count
 */
SemanticAnalyzer* create_semantic_analyzer() {
    // TODO: Allocate and initialize SemanticAnalyzer
    SemanticAnalyzer* analyzer = malloc(sizeof(SemanticAnalyzer));
    analyzer->global_scope = create_symbol_table(NULL, 0);
    analyzer->current_scope = analyzer->global_scope;
    analyzer->current_function = NULL;
    analyzer->error_count = 0;
    analyzer->scope_level = 0;
    return analyzer;
}

// Free semantic analyzer
void free_semantic_analyzer(SemanticAnalyzer* analyzer) {
    // TODO: Free all symbol tables
    // Note: Be careful with nested scopes
    free(analyzer);
}

/*
 * TODO 3: Implement scope management
 * 
 * Guidelines:
 * - Enter new scope when entering { }
 * - Exit scope when leaving { }
 * - Create new symbol table for each scope
 * - Link to parent scope for lookup
 */
void enter_scope(SemanticAnalyzer* analyzer) {
    // TODO: Create new scope and push onto scope stack
    analyzer->scope_level++;
    SymbolTable* new_scope = create_symbol_table(analyzer->current_scope, 
                                                  analyzer->scope_level);
    analyzer->current_scope = new_scope;
}

void exit_scope(SemanticAnalyzer* analyzer) {
    // TODO: Pop scope and restore parent scope
    if (!analyzer->current_scope->parent) {
        fprintf(stderr, "Error: Cannot exit global scope\n");
        return;
    }
    
    SymbolTable* old_scope = analyzer->current_scope;
    analyzer->current_scope = old_scope->parent;
    analyzer->scope_level--;
    free_symbol_table(old_scope);
}

/*
 * TODO 4: Implement error reporting
 * 
 * Guidelines:
 * - Report errors with line and column numbers
 * - Keep count of errors
 * - Continue analysis after errors when possible
 */
void semantic_error(SemanticAnalyzer* analyzer, int line, int col, 
                     const char* message) {
    fprintf(stderr, "Semantic error at line %d, column %d: %s\n", 
            line, col, message);
    analyzer->error_count++;
}

void semantic_error_node(SemanticAnalyzer* analyzer, ASTNode* node, 
                          const char* message) {
    semantic_error(analyzer, node->line, node->column, message);
}

/*
 * TODO 5: Implement type checking utilities
 * 
 * Guidelines:
 * - Compare types for compatibility
 * - Check implicit conversions (int to char, etc.)
 * - Validate operator type requirements
 */

// Check if two types are compatible
bool types_compatible(TypeInfo* t1, TypeInfo* t2) {
    // TODO: Implement type compatibility checking
    // - Same base type
    // - Same pointer level
    // - Consider implicit conversions (int ↔ char)
    return false;
}

// Check if type is arithmetic (int, char)
bool is_arithmetic_type(TypeInfo* type) {
    // TODO: Check if type supports arithmetic operations
    return false;
}

// Check if type is boolean-compatible (for conditions)
bool is_boolean_type(TypeInfo* type) {
    // TODO: In C, any arithmetic type or pointer can be used in boolean context
    return false;
}

// Check if type is pointer
bool is_pointer_type(TypeInfo* type) {
    // TODO: Check if pointer_level > 0
    return false;
}

/*
 * TODO 6: Implement expression type checking
 * 
 * Guidelines:
 * - Calculate result type of expressions
 * - Check operand types are valid for operator
 * - Fill in type_info field of expression nodes
 * - Return the type of the expression
 */

// Forward declaration
TypeInfo* analyze_expression(SemanticAnalyzer* analyzer, ASTNode* expr);

// Analyze binary operation
TypeInfo* analyze_binary_op(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement binary operation type checking
    // 1. Analyze left and right operands
    // 2. Check operands are compatible with operator
    // 3. Determine result type
    // 4. Fill in node->type_info
    // 
    // Arithmetic operators (+, -, *, /, %):
    //   - Both operands must be arithmetic
    //   - Result type is arithmetic
    // 
    // Relational operators (<, >, <=, >=):
    //   - Both operands must be arithmetic
    //   - Result type is int (boolean)
    // 
    // Equality operators (==, !=):
    //   - Operands must be compatible types
    //   - Result type is int (boolean)
    // 
    // Logical operators (&&, ||):
    //   - Operands must be boolean-compatible
    //   - Result type is int (boolean)
    
    return NULL;
}

// Analyze unary operation
TypeInfo* analyze_unary_op(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement unary operation type checking
    // 
    // Negation (-):
    //   - Operand must be arithmetic
    //   - Result type same as operand
    // 
    // Logical NOT (!):
    //   - Operand must be boolean-compatible
    //   - Result type is int (boolean)
    // 
    // Address-of (&):
    //   - Operand must be lvalue (variable, array element)
    //   - Result is pointer to operand type
    // 
    // Dereference (*):
    //   - Operand must be pointer
    //   - Result is pointed-to type
    
    return NULL;
}

// Analyze assignment
TypeInfo* analyze_assignment(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement assignment type checking
    // 1. Analyze left-hand side (must be lvalue)
    // 2. Analyze right-hand side
    // 3. Check types are compatible
    // 4. Result type is type of lhs
    
    return NULL;
}

// Analyze function call
TypeInfo* analyze_call(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement function call type checking
    // 1. Look up function in symbol table
    // 2. Check function exists
    // 3. Count arguments
    // 4. Check argument count matches parameter count
    // 5. Check each argument type matches parameter type
    // 6. Result type is function return type
    
    return NULL;
}

// Analyze identifier (variable reference)
TypeInfo* analyze_identifier(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement identifier type checking
    // 1. Look up identifier in symbol table
    // 2. Check identifier exists (declared)
    // 3. Fill in type_info from symbol table
    // 4. Return identifier's type
    
    return NULL;
}

// Analyze literal
TypeInfo* analyze_literal(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement literal type checking
    // Determine type based on literal value
    // - All integer literals have type int
    // - String literals have type char*
    // - Character literals have type char
    
    return NULL;
}

// Main expression analysis dispatcher
TypeInfo* analyze_expression(SemanticAnalyzer* analyzer, ASTNode* expr) {
    if (!expr) return NULL;
    
    // TODO: Dispatch to appropriate handler based on expr->type
    switch (expr->type) {
        case AST_BINARY_OP:
            return analyze_binary_op(analyzer, expr);
        case AST_UNARY_OP:
            return analyze_unary_op(analyzer, expr);
        case AST_ASSIGNMENT:
            return analyze_assignment(analyzer, expr);
        case AST_CALL:
            return analyze_call(analyzer, expr);
        case AST_IDENTIFIER:
            return analyze_identifier(analyzer, expr);
        case AST_LITERAL:
            return analyze_literal(analyzer, expr);
        default:
            semantic_error_node(analyzer, expr, "Unknown expression type");
            return NULL;
    }
}

/*
 * TODO 7: Implement statement analysis
 * 
 * Guidelines:
 * - Validate each statement type
 * - Check expressions in statements
 * - Enforce semantic rules (e.g., return in non-void function)
 */

// Forward declaration
void analyze_statement(SemanticAnalyzer* analyzer, ASTNode* stmt);

// Analyze return statement
void analyze_return(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement return statement analysis
    // 1. Check we're inside a function
    // 2. Analyze return value expression
    // 3. Check return type matches function return type
}

// Analyze if statement
void analyze_if(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement if statement analysis
    // 1. Analyze condition expression
    // 2. Check condition is boolean-compatible
    // 3. Analyze then branch
    // 4. Analyze else branch if present
}

// Analyze while statement
void analyze_while(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement while statement analysis
    // Similar to if statement
}

// Analyze for statement
void analyze_for(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement for statement analysis
    // 1. Analyze initialization expression
    // 2. Analyze condition expression
    // 3. Analyze increment expression
    // 4. Analyze body statement
}

// Analyze compound statement (block)
void analyze_compound(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement compound statement analysis
    // 1. Enter new scope
    // 2. Analyze each statement in block
    // 3. Exit scope
}

// Analyze declaration
void analyze_declaration(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Implement declaration analysis
    // 1. Check variable not already declared in current scope
    // 2. Insert variable into symbol table
    // 3. If initializer present, analyze it and check type compatibility
}

// Analyze expression statement
void analyze_expr_stmt(SemanticAnalyzer* analyzer, ASTNode* node) {
    // TODO: Simply analyze the expression
    analyze_expression(analyzer, node->data.expr_stmt.expr);
}

// Main statement analysis dispatcher
void analyze_statement(SemanticAnalyzer* analyzer, ASTNode* stmt) {
    if (!stmt) return;
    
    // TODO: Dispatch based on statement type
    switch (stmt->type) {
        case AST_RETURN:
            analyze_return(analyzer, stmt);
            break;
        case AST_IF:
            analyze_if(analyzer, stmt);
            break;
        case AST_WHILE:
            analyze_while(analyzer, stmt);
            break;
        case AST_FOR:
            analyze_for(analyzer, stmt);
            break;
        case AST_COMPOUND:
            analyze_compound(analyzer, stmt);
            break;
        case AST_DECLARATION:
            analyze_declaration(analyzer, stmt);
            break;
        case AST_EXPR_STMT:
            analyze_expr_stmt(analyzer, stmt);
            break;
        default:
            semantic_error_node(analyzer, stmt, "Unknown statement type");
            break;
    }
}

/*
 * TODO 8: Implement function analysis
 * 
 * Guidelines:
 * - Register function in global symbol table
 * - Register parameters in function scope
 * - Analyze function body
 * - Check return paths (non-void functions must return)
 */
void analyze_function(SemanticAnalyzer* analyzer, ASTNode* func) {
    // TODO: Implement function analysis
    // 1. Check function not already declared
    // 2. Insert function into global symbol table
    // 3. Set as current function
    // 4. Enter new scope for function body
    // 5. Insert parameters into scope
    // 6. Analyze function body
    // 7. Check return statements
    // 8. Exit scope
}

/*
 * TODO 9: Implement program analysis
 * 
 * Guidelines:
 * - Analyze each function in program
 * - Check for main function
 * - Ensure no duplicate function names
 */
void analyze_program(SemanticAnalyzer* analyzer, ASTNode* program) {
    // TODO: Implement program analysis
    // 1. Iterate through all function definitions
    // 2. Analyze each function
    // 3. Check that 'main' function exists
    // 4. Verify main has correct signature (int main() or int main(int, char**))
}

/*
 * Main semantic analysis entry point
 */
bool semantic_analyze(ASTNode* ast) {
    if (!ast) {
        fprintf(stderr, "Error: NULL AST passed to semantic analyzer\n");
        return false;
    }
    
    SemanticAnalyzer* analyzer = create_semantic_analyzer();
    
    analyze_program(analyzer, ast);
    
    bool success = (analyzer->error_count == 0);
    if (success) {
        printf("Semantic analysis completed successfully\n");
    } else {
        fprintf(stderr, "Semantic analysis failed with %d error(s)\n", 
                analyzer->error_count);
    }
    
    free_semantic_analyzer(analyzer);
    return success;
}

/*
 * Test main (for standalone testing)
 */
int main(int argc, char** argv) {
    printf("Semantic analyzer template - implement the TODO sections\n");
    printf("This analyzer will type-check and validate the AST\n");
    
    // TODO: Integrate with parser
    // Token** tokens = tokenize(source_code);
    // ASTNode* ast = parse(tokens);
    // bool success = semantic_analyze(ast);
    // if (success) {
    //     // Proceed to code generation
    // }
    // free_ast(ast);
    
    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Implement symbol table operations
 *         Test: insert symbols, lookup, handle scopes
 * 
 * Step 2: Implement scope management
 *         Test: enter/exit scopes, symbol shadowing
 * 
 * Step 3: Implement simple expression type checking
 *         Test: literals, identifiers, binary operations
 * 
 * Step 4: Implement declaration analysis
 *         Test: variable declarations, duplicate detection
 * 
 * Step 5: Implement statement analysis
 *         Test: return statements, if statements, loops
 * 
 * Step 6: Implement function analysis
 *         Test: function declarations, parameter checking
 * 
 * Step 7: Implement function call checking
 *         Test: argument count, argument types
 * 
 * Step 8: Add advanced type checking
 *         Test: pointers, type conversions, complex expressions
 * 
 * Testing Strategy:
 * - Test with semantically correct programs first
 * - Then test error cases (undeclared variables, type mismatches)
 * - Check error messages are clear and helpful
 * - Verify symbol table contents at each scope
 * - Test nested scopes and shadowing
 * 
 * Common Semantic Errors to Detect:
 * - Undeclared variables
 * - Duplicate declarations in same scope
 * - Type mismatches in assignments
 * - Wrong number of function arguments
 * - Wrong types of function arguments
 * - Return type mismatches
 * - Using void-type values
 * - Dereferencing non-pointers
 * - Array index not integer
 * - Calling non-functions
 * 
 * Extensions:
 * - Constant folding (evaluate constant expressions)
 * - Dead code detection
 * - Unused variable warnings
 * - Implicit type conversions
 * - Struct/union support
 * - Array type checking
 */
