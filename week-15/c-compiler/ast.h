/*
 * Simple C Compiler - Abstract Syntax Tree (AST) Definitions
 * 
 * This header defines the data structures for representing the parse tree
 * and abstract syntax tree for our C compiler.
 * 
 * The AST is a tree representation of the source code that captures its
 * syntactic structure without the syntactic sugar and noise tokens.
 */

#ifndef AST_H
#define AST_H

#include <stdlib.h>
#include <string.h>

/*
 * AST Node Types
 * 
 * These represent the different kinds of nodes in our abstract syntax tree.
 * Each node type corresponds to a language construct in C.
 */
typedef enum {
    // Program structure
    AST_PROGRAM,        // Root node: entire program
    AST_FUNCTION,       // Function definition
    
    // Statements
    AST_COMPOUND,       // Compound statement (block with { })
    AST_RETURN,         // Return statement
    AST_IF,             // If statement
    AST_WHILE,          // While loop
    AST_FOR,            // For loop
    AST_EXPR_STMT,      // Expression statement (expr;)
    AST_DECLARATION,    // Variable declaration
    
    // Expressions
    AST_BINARY_OP,      // Binary operation (+, -, *, /, ==, !=, etc.)
    AST_UNARY_OP,       // Unary operation (-, !, &, *)
    AST_ASSIGNMENT,     // Assignment (=)
    AST_CALL,           // Function call
    AST_IDENTIFIER,     // Variable or function name
    AST_LITERAL,        // Literal value (number, string)
    
    // Types
    AST_TYPE,           // Type specification (int, char, etc.)
    AST_PARAM,          // Function parameter
} ASTNodeType;

/*
 * Data Types
 * 
 * These represent the primitive and derived types in our C subset.
 */
typedef enum {
    TYPE_INT,
    TYPE_CHAR,
    TYPE_VOID,
    TYPE_POINTER,
    TYPE_ARRAY,
    TYPE_FUNCTION,
    TYPE_UNKNOWN
} DataType;

/*
 * Binary Operators
 */
typedef enum {
    OP_ADD,         // +
    OP_SUB,         // -
    OP_MUL,         // *
    OP_DIV,         // /
    OP_MOD,         // %
    OP_EQ,          // ==
    OP_NE,          // !=
    OP_LT,          // <
    OP_GT,          // >
    OP_LE,          // <=
    OP_GE,          // >=
    OP_AND,         // &&
    OP_OR,          // ||
} BinaryOp;

/*
 * Unary Operators
 */
typedef enum {
    OP_NEG,         // -
    OP_NOT,         // !
    OP_ADDR,        // & (address-of)
    OP_DEREF,       // * (dereference)
} UnaryOp;

/*
 * Forward declaration of AST node structure
 */
struct ASTNode;

/*
 * Type Information Structure
 * 
 * Stores detailed type information for variables and expressions.
 */
typedef struct {
    DataType base_type;
    int pointer_level;      // 0 for non-pointer, 1 for *, 2 for **, etc.
    int array_size;         // For array types, -1 if not array
    struct ASTNode* params; // For function types: linked list of parameters
    DataType return_type;   // For function types
} TypeInfo;

/*
 * AST Node Structure
 * 
 * This is the main node structure used throughout the AST.
 * Different node types use different fields in the union.
 * 
 * Guidelines for implementation:
 * - Use type field to determine which union member is valid
 * - Always set line and column for error reporting
 * - Use next pointer for lists (e.g., statement lists, parameter lists)
 */
typedef struct ASTNode {
    ASTNodeType type;
    TypeInfo* type_info;    // Type information (filled during semantic analysis)
    int line;
    int column;
    
    union {
        // Program node: list of functions
        struct {
            struct ASTNode* functions;
        } program;
        
        // Function node: name, return type, parameters, body
        struct {
            char* name;
            TypeInfo* return_type;
            struct ASTNode* params;
            struct ASTNode* body;
        } function;
        
        // Compound statement: list of statements
        struct {
            struct ASTNode* statements;
        } compound;
        
        // Return statement: return value expression
        struct {
            struct ASTNode* expr;
        } ret;
        
        // If statement: condition, then branch, else branch
        struct {
            struct ASTNode* condition;
            struct ASTNode* then_branch;
            struct ASTNode* else_branch;
        } if_stmt;
        
        // While statement: condition, body
        struct {
            struct ASTNode* condition;
            struct ASTNode* body;
        } while_stmt;
        
        // For statement: init, condition, increment, body
        struct {
            struct ASTNode* init;
            struct ASTNode* condition;
            struct ASTNode* increment;
            struct ASTNode* body;
        } for_stmt;
        
        // Expression statement: expression
        struct {
            struct ASTNode* expr;
        } expr_stmt;
        
        // Declaration: type, name, initializer
        struct {
            TypeInfo* var_type;
            char* name;
            struct ASTNode* initializer;
        } declaration;
        
        // Binary operation: operator, left operand, right operand
        struct {
            BinaryOp op;
            struct ASTNode* left;
            struct ASTNode* right;
        } binary;
        
        // Unary operation: operator, operand
        struct {
            UnaryOp op;
            struct ASTNode* operand;
        } unary;
        
        // Assignment: left-hand side, right-hand side
        struct {
            struct ASTNode* lhs;
            struct ASTNode* rhs;
        } assignment;
        
        // Function call: name, arguments
        struct {
            char* name;
            struct ASTNode* args;
        } call;
        
        // Identifier: name
        struct {
            char* name;
        } identifier;
        
        // Literal: value (stored as string, convert as needed)
        struct {
            char* value;
        } literal;
        
        // Parameter: type, name
        struct {
            TypeInfo* param_type;
            char* name;
        } param;
    } data;
    
    struct ASTNode* next;   // For linked lists of nodes
} ASTNode;

/*
 * AST Construction Functions
 * 
 * These helper functions create and initialize AST nodes.
 * Implement these in parser.c or a separate ast.c file.
 */

// Create a new AST node with the given type
ASTNode* create_ast_node(ASTNodeType type, int line, int column);

// Program nodes
ASTNode* create_program_node(ASTNode* functions);

// Function nodes
ASTNode* create_function_node(char* name, TypeInfo* return_type, 
                               ASTNode* params, ASTNode* body, 
                               int line, int column);

// Statement nodes
ASTNode* create_compound_node(ASTNode* statements, int line, int column);
ASTNode* create_return_node(ASTNode* expr, int line, int column);
ASTNode* create_if_node(ASTNode* condition, ASTNode* then_branch, 
                        ASTNode* else_branch, int line, int column);
ASTNode* create_while_node(ASTNode* condition, ASTNode* body, 
                           int line, int column);
ASTNode* create_for_node(ASTNode* init, ASTNode* condition, 
                         ASTNode* increment, ASTNode* body, 
                         int line, int column);
ASTNode* create_expr_stmt_node(ASTNode* expr, int line, int column);
ASTNode* create_declaration_node(TypeInfo* type, char* name, 
                                  ASTNode* initializer, 
                                  int line, int column);

// Expression nodes
ASTNode* create_binary_node(BinaryOp op, ASTNode* left, ASTNode* right, 
                            int line, int column);
ASTNode* create_unary_node(UnaryOp op, ASTNode* operand, 
                           int line, int column);
ASTNode* create_assignment_node(ASTNode* lhs, ASTNode* rhs, 
                                int line, int column);
ASTNode* create_call_node(char* name, ASTNode* args, int line, int column);
ASTNode* create_identifier_node(char* name, int line, int column);
ASTNode* create_literal_node(char* value, int line, int column);

// Parameter nodes
ASTNode* create_param_node(TypeInfo* type, char* name, int line, int column);

// Type information functions
TypeInfo* create_type_info(DataType base_type);
void free_type_info(TypeInfo* type);

// AST traversal and utility functions
void free_ast(ASTNode* node);
void print_ast(ASTNode* node, int indent);

// AST node list helpers
ASTNode* append_ast_node(ASTNode* list, ASTNode* node);
int count_ast_nodes(ASTNode* list);

#endif // AST_H

/*
 * IMPLEMENTATION NOTES:
 * 
 * Memory Management:
 * - Each create_*_node function should allocate memory with malloc
 * - Remember to free all strings (char*) that are dynamically allocated
 * - The free_ast function should recursively free all child nodes
 * 
 * Linked Lists:
 * - Use the 'next' pointer to create linked lists of nodes
 * - Example: list of statements in a compound statement
 * - Example: list of parameters in a function definition
 * - Example: list of arguments in a function call
 * 
 * Error Handling:
 * - Store line and column numbers for all nodes
 * - This allows detailed error messages during semantic analysis
 * 
 * Type Information:
 * - type_info starts as NULL in parser
 * - Filled in during semantic analysis phase
 * - Used for type checking and code generation
 */
