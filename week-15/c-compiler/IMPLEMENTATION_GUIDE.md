# C Compiler Implementation Guide

This guide provides detailed, step-by-step instructions for implementing a complete C compiler from scratch. Each phase builds upon the previous one, creating a functional compiler that can translate C source code to executable machine code.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Lexical Analysis (Lexer)](#phase-1-lexical-analysis)
4. [Phase 2: Syntax Analysis (Parser)](#phase-2-syntax-analysis)
5. [Phase 3: Semantic Analysis](#phase-3-semantic-analysis)
6. [Phase 4: Code Generation](#phase-4-code-generation)
7. [Phase 5: Optimization](#phase-5-optimization)
8. [Testing and Validation](#testing-and-validation)
9. [Complete Examples](#complete-examples)
10. [Resources and References](#resources-and-references)

## Project Overview

### What You'll Build

A complete C compiler with these components:
- **Lexer**: Breaks source code into tokens
- **Parser**: Builds an Abstract Syntax Tree (AST) from tokens
- **Semantic Analyzer**: Type checking and validation
- **Code Generator**: Produces x86-64 assembly code
- **Optimizer**: Improves code quality

### Supported C Subset

Our compiler supports:
- **Data types**: `int`, `char`, `void`, pointers
- **Control flow**: `if`, `else`, `while`, `for`, `return`
- **Operators**: Arithmetic (`+`, `-`, `*`, `/`, `%`), comparison (`==`, `!=`, `<`, `>`, `<=`, `>=`), logical (`&&`, `||`, `!`)
- **Functions**: Definition and calls
- **Variables**: Declaration, assignment, scope

### Architecture

```
Source Code (.c)
    ↓
[Lexer] → Tokens
    ↓
[Parser] → Abstract Syntax Tree (AST)
    ↓
[Semantic Analyzer] → Type-checked AST
    ↓
[Optimizer] → Optimized AST
    ↓
[Code Generator] → Assembly (.s)
    ↓
[Assembler/Linker] → Executable
```

## Prerequisites

### Required Knowledge

- **C programming**: Pointers, structures, memory management
- **Data structures**: Trees, hash tables, linked lists
- **Algorithms**: Recursion, tree traversal
- **Basic compiler theory**: Helpful but not required

### Tools Needed

- GCC or Clang compiler
- Make build system
- Text editor or IDE
- Debugger (GDB) for troubleshooting

### Setting Up

```bash
cd c-compiler/
make help              # See available targets
make lexer            # Build just the lexer
make all              # Build all components
```

## Phase 1: Lexical Analysis

### Overview

The lexer (tokenizer) breaks source code into meaningful units called **tokens**. It's the first phase of compilation.

### What is a Token?

A token is a categorized unit of source code:
- **Keywords**: `int`, `return`, `if`, `while`
- **Identifiers**: Variable and function names
- **Literals**: Numbers, strings
- **Operators**: `+`, `-`, `==`, `!=`
- **Delimiters**: `;`, `(`, `)`, `{`, `}`

### Implementation Steps

#### Step 1: Define Token Types (10 minutes)

Open `lexer.c` and define all token types in the enum:

```c
typedef enum {
    // Keywords
    TOKEN_INT, TOKEN_CHAR, TOKEN_VOID,
    TOKEN_RETURN, TOKEN_IF, TOKEN_ELSE, 
    TOKEN_WHILE, TOKEN_FOR,
    
    // Identifiers and literals
    TOKEN_IDENT, TOKEN_NUMBER, TOKEN_STRING,
    
    // Operators
    TOKEN_PLUS, TOKEN_MINUS, TOKEN_STAR, TOKEN_SLASH, TOKEN_MOD,
    TOKEN_ASSIGN, TOKEN_EQ, TOKEN_NE,
    TOKEN_LT, TOKEN_GT, TOKEN_LE, TOKEN_GE,
    TOKEN_AND, TOKEN_OR, TOKEN_NOT,
    
    // Delimiters
    TOKEN_SEMI, TOKEN_COMMA,
    TOKEN_LPAREN, TOKEN_RPAREN,
    TOKEN_LBRACE, TOKEN_RBRACE,
    TOKEN_LBRACKET, TOKEN_RBRACKET,
    
    // Special
    TOKEN_EOF, TOKEN_ERROR
} TokenType;
```

**Test**: Compile and run: `make lexer && ./lexer`

#### Step 2: Implement Keyword Recognition (15 minutes)

Complete the `is_keyword()` function:

```c
TokenType is_keyword(const char* str) {
    if (strcmp(str, "int") == 0) return TOKEN_INT;
    if (strcmp(str, "char") == 0) return TOKEN_CHAR;
    if (strcmp(str, "void") == 0) return TOKEN_VOID;
    if (strcmp(str, "return") == 0) return TOKEN_RETURN;
    if (strcmp(str, "if") == 0) return TOKEN_IF;
    if (strcmp(str, "else") == 0) return TOKEN_ELSE;
    if (strcmp(str, "while") == 0) return TOKEN_WHILE;
    if (strcmp(str, "for") == 0) return TOKEN_FOR;
    return TOKEN_IDENT;  // Not a keyword
}
```

**Test**: Create a test with keywords and verify recognition.

#### Step 3: Implement Single-Character Tokens (20 minutes)

In `get_next_token()`, handle simple single-character tokens:

```c
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
    
    // Single-character tokens
    switch (*p) {
        case '+': 
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_PLUS, "+", *line, start_col);
        case '-':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_MINUS, "-", *line, start_col);
        case '*':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_STAR, "*", *line, start_col);
        case '/':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_SLASH, "/", *line, start_col);
        case ';':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_SEMI, ";", *line, start_col);
        case '(':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_LPAREN, "(", *line, start_col);
        case ')':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_RPAREN, ")", *line, start_col);
        case '{':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_LBRACE, "{", *line, start_col);
        case '}':
            (*column)++;
            *input = p + 1;
            return create_token(TOKEN_RBRACE, "}", *line, start_col);
    }
    
    // More cases...
}
```

**Test**: `int main() { return 0; }` should tokenize correctly.

#### Step 4: Implement Number Literals (15 minutes)

Add number recognition:

```c
// Inside get_next_token(), after single-char tokens:
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
```

**Test**: `42`, `123`, `0` should tokenize as numbers.

#### Step 5: Implement Identifiers (15 minutes)

Add identifier recognition:

```c
// After number recognition:
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
```

**Test**: `main`, `x`, `count` should tokenize as identifiers.

#### Step 6: Implement Multi-Character Operators (20 minutes)

Handle operators like `==`, `!=`, `<=`, `>=`:

```c
// In switch statement, modify '=' case:
case '=':
    if (*(p + 1) == '=') {
        // == operator
        (*column) += 2;
        *input = p + 2;
        return create_token(TOKEN_EQ, "==", *line, start_col);
    } else {
        // = operator
        (*column)++;
        *input = p + 1;
        return create_token(TOKEN_ASSIGN, "=", *line, start_col);
    }

case '<':
    if (*(p + 1) == '=') {
        (*column) += 2;
        *input = p + 2;
        return create_token(TOKEN_LE, "<=", *line, start_col);
    } else {
        (*column)++;
        *input = p + 1;
        return create_token(TOKEN_LT, "<", *line, start_col);
    }

// Similar for '>', '!'
```

**Test**: `==`, `!=`, `<=`, `>=` should tokenize correctly.

#### Step 7: Implement Complete Tokenization (10 minutes)

Complete the `tokenize()` function:

```c
Token** tokenize(const char* input) {
    int capacity = 128;
    Token** tokens = malloc(sizeof(Token*) * capacity);
    int count = 0;
    
    int line = 1, column = 1;
    
    while (true) {
        Token* token = get_next_token(&input, &line, &column);
        
        if (count >= capacity - 1) {
            capacity *= 2;
            tokens = realloc(tokens, sizeof(Token*) * capacity);
        }
        
        tokens[count++] = token;
        
        if (token->type == TOKEN_EOF || token->type == TOKEN_ERROR) {
            break;
        }
    }
    
    tokens[count] = NULL;  // Null-terminate
    return tokens;
}
```

**Test**: Run full lexer test with sample C code.

### Testing the Lexer

Create test cases in `main()`:

```c
const char* test1 = "int main() { return 0; }";
const char* test2 = "int x = 42 + 10;";
const char* test3 = "if (x == 5) { return 1; }";

// Test each and print tokens
```

**Expected output**:
```
Token: INT 'int' (line 1, col 1)
Token: IDENT 'main' (line 1, col 5)
Token: LPAREN '(' (line 1, col 9)
...
```

## Phase 2: Syntax Analysis

### Overview

The parser builds an **Abstract Syntax Tree (AST)** from tokens. The AST represents the program's structure without syntax noise.

### Key Concepts

#### Grammar

A grammar defines the syntax rules. Example:

```
expression → term (('+' | '-') term)*
term → factor (('*' | '/') factor)*
factor → NUMBER | IDENT | '(' expression ')'
```

#### Recursive Descent Parsing

Each grammar rule becomes a function:
- `parse_expression()` for `expression` rule
- `parse_term()` for `term` rule
- `parse_factor()` for `factor` rule

Functions call each other recursively, mirroring the grammar structure.

### Implementation Steps

#### Step 1: Implement Token Access Functions (15 minutes)

```c
Token* peek(Parser* parser) {
    return parser->tokens[parser->current];
}

Token* previous(Parser* parser) {
    return parser->tokens[parser->current - 1];
}

bool is_at_end(Parser* parser) {
    return peek(parser)->type == TOKEN_EOF;
}

Token* advance(Parser* parser) {
    if (!is_at_end(parser)) {
        parser->current++;
    }
    return previous(parser);
}

bool check(Parser* parser, TokenType type) {
    if (is_at_end(parser)) return false;
    return peek(parser)->type == type;
}

bool match(Parser* parser, TokenType type) {
    if (check(parser, type)) {
        advance(parser);
        return true;
    }
    return false;
}
```

**Test**: Create parser, feed tokens, test access functions.

#### Step 2: Implement Primary Expression Parsing (20 minutes)

Parse the simplest expressions:

```c
ASTNode* parse_primary(Parser* parser) {
    Token* token = peek(parser);
    
    // Number literal
    if (match(parser, TOKEN_NUMBER)) {
        return create_literal_node(previous(parser)->value, 
                                   token->line, token->column);
    }
    
    // Identifier
    if (match(parser, TOKEN_IDENT)) {
        return create_identifier_node(previous(parser)->value,
                                      token->line, token->column);
    }
    
    // Parenthesized expression
    if (match(parser, TOKEN_LPAREN)) {
        ASTNode* expr = parse_expression(parser);
        expect(parser, TOKEN_RPAREN, "Expected ')' after expression");
        return expr;
    }
    
    parser_error(parser, "Expected expression");
    return NULL;
}
```

**Test**: Parse `42`, `x`, `(10 + 20)`

#### Step 3: Implement Binary Operators with Precedence (30 minutes)

Implement each precedence level:

```c
// Multiplicative: * /
ASTNode* parse_multiplicative(Parser* parser) {
    ASTNode* left = parse_unary(parser);
    
    while (match(parser, TOKEN_STAR) || match(parser, TOKEN_SLASH)) {
        Token* op_token = previous(parser);
        BinaryOp op = (op_token->type == TOKEN_STAR) ? OP_MUL : OP_DIV;
        ASTNode* right = parse_unary(parser);
        left = create_binary_node(op, left, right, 
                                  op_token->line, op_token->column);
    }
    
    return left;
}

// Additive: + -
ASTNode* parse_additive(Parser* parser) {
    ASTNode* left = parse_multiplicative(parser);
    
    while (match(parser, TOKEN_PLUS) || match(parser, TOKEN_MINUS)) {
        Token* op_token = previous(parser);
        BinaryOp op = (op_token->type == TOKEN_PLUS) ? OP_ADD : OP_SUB;
        ASTNode* right = parse_multiplicative(parser);
        left = create_binary_node(op, left, right,
                                  op_token->line, op_token->column);
    }
    
    return left;
}

// Continue for equality, relational, logical operators...
```

**Test**: Parse `2 + 3`, `5 * 6`, `2 + 3 * 4` (should build correct tree)

#### Step 4: Implement Statement Parsing (40 minutes)

Parse different statement types:

```c
ASTNode* parse_statement(Parser* parser) {
    // Return statement
    if (match(parser, TOKEN_RETURN)) {
        Token* token = previous(parser);
        ASTNode* expr = parse_expression(parser);
        expect(parser, TOKEN_SEMI, "Expected ';' after return");
        return create_return_node(expr, token->line, token->column);
    }
    
    // If statement
    if (match(parser, TOKEN_IF)) {
        Token* token = previous(parser);
        expect(parser, TOKEN_LPAREN, "Expected '(' after 'if'");
        ASTNode* condition = parse_expression(parser);
        expect(parser, TOKEN_RPAREN, "Expected ')' after condition");
        ASTNode* then_branch = parse_statement(parser);
        ASTNode* else_branch = NULL;
        if (match(parser, TOKEN_ELSE)) {
            else_branch = parse_statement(parser);
        }
        return create_if_node(condition, then_branch, else_branch,
                             token->line, token->column);
    }
    
    // Compound statement (block)
    if (match(parser, TOKEN_LBRACE)) {
        return parse_compound(parser);
    }
    
    // Declaration or expression statement
    // ...
}
```

**Test**: Parse `return 0;`, `if (x > 0) return 1;`

#### Step 5: Implement Function Parsing (30 minutes)

```c
ASTNode* parse_function(Parser* parser) {
    Token* token = peek(parser);
    
    // Parse return type
    TypeInfo* return_type = parse_type(parser);
    
    // Parse function name
    Token* name_token = expect(parser, TOKEN_IDENT, 
                               "Expected function name");
    
    // Parse parameters
    expect(parser, TOKEN_LPAREN, "Expected '(' after function name");
    ASTNode* params = parse_parameters(parser);
    expect(parser, TOKEN_RPAREN, "Expected ')' after parameters");
    
    // Parse body
    ASTNode* body = parse_compound(parser);
    
    return create_function_node(name_token->value, return_type, 
                                params, body,
                                token->line, token->column);
}
```

**Test**: Parse `int main() { return 0; }`

### Testing the Parser

Create comprehensive tests:

```c
// Test 1: Simple function
const char* src1 = "int main() { return 0; }";
Token** tokens1 = tokenize(src1);
ASTNode* ast1 = parse(tokens1);
print_ast(ast1, 0);

// Test 2: Function with variables
const char* src2 = "int add(int a, int b) { return a + b; }";
// ...
```

## Phase 3: Semantic Analysis

### Overview

Semantic analysis ensures the program is **meaningful**:
- Variables are declared before use
- Types are used correctly
- Functions are called with correct arguments

### Key Concepts

#### Symbol Table

Tracks declared identifiers and their types:

```c
Symbol Table (Scope 0 - Global):
  main: function, returns int

Symbol Table (Scope 1 - main):
  x: variable, type int
  y: variable, type int
```

#### Type Checking

Validates operations on types:
- `int + int` → valid
- `int * pointer` → invalid
- `func(int, int)` with `func(int)` → error (wrong arg count)

### Implementation Steps

#### Step 1: Implement Symbol Table (30 minutes)

```c
bool insert_symbol(SymbolTable* table, const char* name, 
                   TypeInfo* type, bool is_function, int param_count) {
    // Check for duplicate in current scope
    Symbol* existing = lookup_symbol_current_scope(table, name);
    if (existing) {
        return false;  // Already declared
    }
    
    // Create new symbol
    Symbol* symbol = malloc(sizeof(Symbol));
    symbol->name = strdup(name);
    symbol->type = type;
    symbol->scope_level = table->scope_level;
    symbol->is_function = is_function;
    symbol->param_count = param_count;
    
    // Insert into hash table
    unsigned int bucket = hash_symbol(name);
    symbol->next = table->buckets[bucket];
    table->buckets[bucket] = symbol;
    
    return true;
}

Symbol* lookup_symbol(SymbolTable* table, const char* name) {
    // Search current and parent scopes
    SymbolTable* current = table;
    while (current) {
        unsigned int bucket = hash_symbol(name);
        Symbol* sym = current->buckets[bucket];
        while (sym) {
            if (strcmp(sym->name, name) == 0) {
                return sym;
            }
            sym = sym->next;
        }
        current = current->parent;
    }
    return NULL;  // Not found
}
```

**Test**: Insert symbols, lookup, test scoping

#### Step 2: Implement Type Checking for Expressions (40 minutes)

```c
TypeInfo* analyze_binary_op(SemanticAnalyzer* analyzer, ASTNode* node) {
    // Analyze operands
    TypeInfo* left_type = analyze_expression(analyzer, 
                                             node->data.binary.left);
    TypeInfo* right_type = analyze_expression(analyzer, 
                                              node->data.binary.right);
    
    if (!left_type || !right_type) {
        return NULL;  // Error in operands
    }
    
    // Check operator requirements
    BinaryOp op = node->data.binary.op;
    
    if (op == OP_ADD || op == OP_SUB || op == OP_MUL || op == OP_DIV) {
        // Arithmetic operators require arithmetic types
        if (!is_arithmetic_type(left_type)) {
            semantic_error_node(analyzer, node->data.binary.left,
                              "Left operand must be arithmetic type");
            return NULL;
        }
        if (!is_arithmetic_type(right_type)) {
            semantic_error_node(analyzer, node->data.binary.right,
                              "Right operand must be arithmetic type");
            return NULL;
        }
        
        // Result type is arithmetic (int for our subset)
        TypeInfo* result = create_type_info(TYPE_INT);
        node->type_info = result;
        return result;
    }
    
    if (op == OP_EQ || op == OP_NE || op == OP_LT || 
        op == OP_GT || op == OP_LE || op == OP_GE) {
        // Comparison operators
        if (!types_compatible(left_type, right_type)) {
            semantic_error_node(analyzer, node,
                              "Incompatible types for comparison");
            return NULL;
        }
        
        // Result is boolean (int in C)
        TypeInfo* result = create_type_info(TYPE_INT);
        node->type_info = result;
        return result;
    }
    
    // ... handle other operators
    return NULL;
}
```

**Test**: Type check `5 + 3`, `x * y`, detect errors in `ptr + ptr`

#### Step 3: Implement Declaration Analysis (20 minutes)

```c
void analyze_declaration(SemanticAnalyzer* analyzer, ASTNode* node) {
    const char* var_name = node->data.declaration.name;
    TypeInfo* var_type = node->data.declaration.var_type;
    
    // Check for duplicate declaration in current scope
    if (lookup_symbol_current_scope(analyzer->current_scope, var_name)) {
        semantic_error_node(analyzer, node, 
                          "Variable already declared in this scope");
        return;
    }
    
    // Insert into symbol table
    insert_symbol(analyzer->current_scope, var_name, var_type, 
                 false, 0);
    
    // Check initializer if present
    if (node->data.declaration.initializer) {
        TypeInfo* init_type = analyze_expression(analyzer, 
                                                 node->data.declaration.initializer);
        if (init_type && !types_compatible(var_type, init_type)) {
            semantic_error_node(analyzer, node,
                              "Initializer type does not match variable type");
        }
    }
}
```

**Test**: Declare variables, detect duplicates, check initializers

#### Step 4: Implement Function Call Validation (30 minutes)

```c
TypeInfo* analyze_call(SemanticAnalyzer* analyzer, ASTNode* node) {
    const char* func_name = node->data.call.name;
    
    // Look up function in symbol table
    Symbol* func_symbol = lookup_symbol(analyzer->current_scope, func_name);
    
    if (!func_symbol) {
        semantic_error_node(analyzer, node, "Undefined function");
        return NULL;
    }
    
    if (!func_symbol->is_function) {
        semantic_error_node(analyzer, node, "Not a function");
        return NULL;
    }
    
    // Count and check arguments
    int arg_count = count_ast_nodes(node->data.call.args);
    if (arg_count != func_symbol->param_count) {
        char buf[256];
        snprintf(buf, sizeof(buf), 
                "Expected %d arguments, got %d",
                func_symbol->param_count, arg_count);
        semantic_error_node(analyzer, node, buf);
        return NULL;
    }
    
    // TODO: Check argument types match parameter types
    
    // Return function's return type
    node->type_info = func_symbol->type;
    return func_symbol->type;
}
```

**Test**: Call functions, detect errors in argument count/types

### Testing Semantic Analysis

```c
// Test 1: Valid program
const char* valid = "int main() { int x = 5; return x; }";
// Should pass

// Test 2: Undeclared variable
const char* invalid1 = "int main() { return y; }";
// Should error: y not declared

// Test 3: Type mismatch
const char* invalid2 = "int main() { int x = 5; return x + \"hello\"; }";
// Should error: can't add int and string

// Test 4: Duplicate declaration
const char* invalid3 = "int main() { int x = 5; int x = 10; }";
// Should error: x already declared
```

## Phase 4: Code Generation

### Overview

Code generation translates the AST to **assembly code**. We target x86-64 assembly (AT&T syntax).

### Key Concepts

#### Registers

x86-64 has 16 general-purpose 64-bit registers:
- `%rax`: Accumulator, return value
- `%rbx`, `%rcx`, `%rdx`: General purpose
- `%rsi`, `%rdi`: Argument passing
- `%rbp`: Base pointer (frame pointer)
- `%rsp`: Stack pointer
- `%r8`-`%r15`: Additional registers

#### Stack Frame

Each function has a stack frame:

```
High addresses
+------------------+
| Return address   |
+------------------+
| Saved %rbp       | ← %rbp points here
+------------------+
| Local var 1      | ← %rbp - 8
+------------------+
| Local var 2      | ← %rbp - 16
+------------------+
| ...              |
+------------------+ ← %rsp
Low addresses
```

#### Calling Convention

x86-64 System V ABI:
- First 6 integer args: `%rdi`, `%rsi`, `%rdx`, `%rcx`, `%r8`, `%r9`
- Return value in `%rax`
- Stack must be 16-byte aligned before `call`

### Implementation Steps

#### Step 1: Implement Function Prologue/Epilogue (20 minutes)

```c
void emit_function_prologue(CodeGenerator* cg, const char* func_name, 
                             int local_space) {
    // Function label
    fprintf(cg->output, ".globl %s\n", func_name);
    fprintf(cg->output, "%s:\n", func_name);
    
    // Save old frame pointer
    emit_op1(cg, "pushq", "%rbp");
    
    // Set up new frame pointer
    emit_op2(cg, "movq", "%rsp", "%rbp");
    
    // Allocate space for locals (16-byte aligned)
    if (local_space > 0) {
        int aligned = ((local_space + 15) / 16) * 16;
        char buf[32];
        snprintf(buf, sizeof(buf), "$%d", aligned);
        emit_op2(cg, "subq", buf, "%rsp");
    }
}

void emit_function_epilogue(CodeGenerator* cg) {
    // Restore stack pointer
    emit_op2(cg, "movq", "%rbp", "%rsp");
    
    // Restore old frame pointer
    emit_op1(cg, "popq", "%rbp");
    
    // Return
    emit_op(cg, "ret");
}
```

**Test**: Generate prologue/epilogue for simple function

#### Step 2: Implement Expression Code Generation (40 minutes)

```c
Register generate_binary_op(CodeGenerator* cg, ASTNode* node, 
                             CodeGenSymbolTable* symtab) {
    // Generate code for left operand
    Register left_reg = generate_expression(cg, node->data.binary.left, 
                                            symtab);
    
    // Generate code for right operand
    Register right_reg = generate_expression(cg, node->data.binary.right, 
                                             symtab);
    
    // Perform operation
    BinaryOp op = node->data.binary.op;
    
    switch (op) {
        case OP_ADD:
            // addq right, left
            emit_op2(cg, "addq", 
                    register_names_64[right_reg], 
                    register_names_64[left_reg]);
            break;
            
        case OP_SUB:
            // subq right, left
            emit_op2(cg, "subq", 
                    register_names_64[right_reg], 
                    register_names_64[left_reg]);
            break;
            
        case OP_MUL:
            // imulq right, left
            emit_op2(cg, "imulq", 
                    register_names_64[right_reg], 
                    register_names_64[left_reg]);
            break;
            
        // ... other operators
    }
    
    // Free right register, keep result in left register
    free_register(cg, right_reg);
    return left_reg;
}
```

**Test**: Generate code for `2 + 3`, `5 * 6`, check assembly output

#### Step 3: Implement Control Flow (30 minutes)

```c
void generate_if(CodeGenerator* cg, ASTNode* node, 
                  CodeGenSymbolTable* symtab) {
    // Generate unique labels
    char* else_label = generate_label(cg, "else");
    char* end_label = generate_label(cg, "end");
    
    // Generate condition
    Register cond_reg = generate_expression(cg, 
                                            node->data.if_stmt.condition, 
                                            symtab);
    
    // Test condition
    emit_op2(cg, "testq", 
            register_names_64[cond_reg], 
            register_names_64[cond_reg]);
    free_register(cg, cond_reg);
    
    // Jump to else if false
    emit_op1(cg, "je", else_label);
    
    // Generate then branch
    generate_statement(cg, node->data.if_stmt.then_branch, symtab);
    
    // Jump to end
    emit_op1(cg, "jmp", end_label);
    
    // Else label
    emit_label(cg, else_label);
    
    // Generate else branch if present
    if (node->data.if_stmt.else_branch) {
        generate_statement(cg, node->data.if_stmt.else_branch, symtab);
    }
    
    // End label
    emit_label(cg, end_label);
    
    free(else_label);
    free(end_label);
}
```

**Test**: Generate code for `if (x > 0) { return 1; } else { return 0; }`

### Testing Code Generation

Create complete programs and generate assembly:

```c
// Test program
const char* src = 
    "int main() {\n"
    "    int x = 5;\n"
    "    int y = 10;\n"
    "    return x + y;\n"
    "}\n";

// Generate code
Token** tokens = tokenize(src);
ASTNode* ast = parse(tokens);
semantic_analyze(ast);
generate_code(ast, "output.s");

// Assemble and run
system("gcc output.s -o program");
system("./program");
system("echo $?");  // Should print 15
```

## Phase 5: Optimization

### Overview

Optimization improves code quality without changing behavior. Common optimizations include:
- **Constant folding**: `2 + 3` → `5`
- **Dead code elimination**: Remove unreachable code
- **Algebraic simplification**: `x * 1` → `x`

### Implementation Steps

#### Step 1: Implement Constant Folding (30 minutes)

Already provided in `optimizer.c`. Test it:

```c
// Before optimization:
// x = 2 + 3;

// After optimization:
// x = 5;
```

#### Step 2: Implement Dead Code Elimination (20 minutes)

Remove unreachable code after `return`:

```c
// Before:
// return 0;
// x = 5;  // Dead

// After:
// return 0;
```

#### Step 3: Test Optimizations (20 minutes)

```c
const char* src = 
    "int main() {\n"
    "    int x = 2 + 3;\n"
    "    return x * 1;\n"
    "}\n";

Token** tokens = tokenize(src);
ASTNode* ast = parse(tokens);
semantic_analyze(ast);

print_ast(ast, 0);  // Before optimization

optimize(ast, 10);  // Run optimizer

print_ast(ast, 0);  // After optimization

// x should be 5 (not 2 + 3)
// return should be just x (not x * 1)
```

## Testing and Validation

### Test Suite Structure

Create a `tests/` directory with test programs:

```
tests/
├── test_arithmetic.c
├── test_control_flow.c
├── test_functions.c
├── test_variables.c
└── test_errors.c
```

### Example Test

`tests/test_arithmetic.c`:
```c
int main() {
    int x = 2 + 3 * 4;  // Should be 14
    int y = (2 + 3) * 4;  // Should be 20
    return x - y;  // Should return -6
}
```

### Automated Testing

```bash
#!/bin/bash
# test.sh

for test in tests/*.c; do
    echo "Testing $test..."
    
    # Compile with our compiler
    ./compiler "$test" -o output.s
    gcc output.s -o test_prog
    ./test_prog
    result=$?
    
    # Compile with GCC for comparison
    gcc "$test" -o test_gcc
    ./test_gcc
    expected=$?
    
    if [ $result -eq $expected ]; then
        echo "✓ PASS"
    else
        echo "✗ FAIL (got $result, expected $expected)"
    fi
done
```

## Complete Examples

### Example 1: Hello World (Simple)

```c
int main() {
    return 0;
}
```

**Assembly output**:
```asm
.globl main
main:
    pushq %rbp
    movq %rsp, %rbp
    movq $0, %rax
    movq %rbp, %rsp
    popq %rbp
    ret
```

### Example 2: Arithmetic

```c
int main() {
    return 2 + 3 * 4;
}
```

**AST** (simplified):
```
PROGRAM
└── FUNCTION (main, returns int)
    └── RETURN
        └── BINARY_OP (+)
            ├── LITERAL (2)
            └── BINARY_OP (*)
                ├── LITERAL (3)
                └── LITERAL (4)
```

**Optimized AST** (after constant folding):
```
PROGRAM
└── FUNCTION (main, returns int)
    └── RETURN
        └── LITERAL (14)
```

### Example 3: Control Flow

```c
int abs(int x) {
    if (x < 0) {
        return -x;
    } else {
        return x;
    }
}

int main() {
    return abs(-5);
}
```

## Resources and References

### Books

1. **"Compilers: Principles, Techniques, and Tools"** (Dragon Book)
   - Aho, Lam, Sethi, Ullman
   - Comprehensive compiler theory

2. **"Engineering a Compiler"**
   - Cooper & Torczon
   - Practical compiler construction

3. **"Modern Compiler Implementation in C"**
   - Appel
   - Hands-on approach with C

### Online Resources

- **Stanford CS143**: Compilers course materials
- **MIT 6.035**: Computer Language Engineering
- **LLVM Tutorial**: Modern compiler infrastructure
- **x86-64 ABI**: Calling conventions and assembly reference

### Tools

- **GCC**: For comparison and assembling output
- **GDB**: Debugging generated code
- **Valgrind**: Memory leak detection
- **objdump**: Inspecting assembly

### Next Steps

After completing the basic compiler:

1. **Add features**:
   - Arrays
   - Structures
   - Pointers (dereference, address-of)
   - More types (float, long, short)

2. **Improve optimization**:
   - Register allocation
   - Loop optimizations
   - Inlining

3. **Better code generation**:
   - Target different architectures (ARM, RISC-V)
   - Generate LLVM IR instead of assembly
   - Add debugging information

4. **Enhance error handling**:
   - Better error messages
   - Error recovery
   - Warnings

5. **Add preprocessor**:
   - `#include` directives
   - `#define` macros
   - Conditional compilation

## Conclusion

You've now built a complete C compiler from scratch! This foundational knowledge applies to:
- Programming language design
- DSL (Domain-Specific Language) creation
- Understanding how compilers work
- Performance optimization
- Low-level programming

Keep experimenting and building on this foundation!
