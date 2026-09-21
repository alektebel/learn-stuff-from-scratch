/*
 * Simple C Compiler - Code Generator Template
 * 
 * This template guides you through building a code generator for C.
 * The code generator takes a type-checked AST and produces assembly code
 * or an intermediate representation (IR).
 * 
 * We'll target x86-64 assembly (AT&T syntax) for this implementation.
 * Alternatively, you could target a custom IR or another architecture.
 * 
 * Code generation phases:
 * 1. Traverse the AST
 * 2. Generate assembly instructions for each node
 * 3. Handle register allocation (simplified)
 * 4. Manage the stack for local variables
 * 5. Generate function prologue and epilogue
 * 6. Emit assembly code to output file
 * 
 * Compilation: gcc -o codegen codegen.c semantic.c parser.c lexer.c -I.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "ast.h"

/*
 * Register Management
 * 
 * Simplified register allocator for x86-64.
 * We'll use a fixed set of registers for expressions.
 */
typedef enum {
    REG_RAX = 0,    // Return value, first expression register
    REG_RCX,        // Second expression register
    REG_RDX,        // Third expression register
    REG_RBX,        // Fourth expression register
    REG_RSI,        // Function arg 2
    REG_RDI,        // Function arg 1
    REG_RSP,        // Stack pointer (special)
    REG_RBP,        // Base pointer (special)
    REG_COUNT
} Register;

const char* register_names_64[] = {
    "%rax", "%rcx", "%rdx", "%rbx", "%rsi", "%rdi", "%rsp", "%rbp"
};

const char* register_names_32[] = {
    "%eax", "%ecx", "%edx", "%ebx", "%esi", "%edi", "%esp", "%ebp"
};

/*
 * Code Generator State
 * 
 * Maintains state during code generation:
 * - Output file for assembly code
 * - Current function being generated
 * - Stack offset for local variables
 * - Label counter for generating unique labels
 * - Register allocation state
 */
typedef struct {
    FILE* output;
    const char* current_function;
    int stack_offset;           // Offset from %rbp for locals
    int label_counter;          // For generating unique labels
    bool registers_used[REG_COUNT];  // Track which registers are in use
    int next_reg;               // Next available register
} CodeGenerator;

/*
 * Variable Location
 * 
 * Tracks where a variable is stored (stack or register).
 */
typedef struct VarLocation {
    char* name;
    int offset;                 // Offset from %rbp (negative for locals)
    bool in_register;
    Register reg;
    struct VarLocation* next;
} VarLocation;

/*
 * Symbol table for tracking variable locations during code generation
 */
typedef struct {
    VarLocation* vars;
} CodeGenSymbolTable;

/*
 * TODO 1: Implement code generator initialization
 * 
 * Guidelines:
 * - Open output file for assembly code
 * - Initialize state (label counter, stack offset, etc.)
 * - Emit assembly header/preamble
 */
CodeGenerator* create_code_generator(const char* output_filename) {
    // TODO: Allocate and initialize CodeGenerator
    CodeGenerator* codegen = malloc(sizeof(CodeGenerator));
    codegen->output = fopen(output_filename, "w");
    if (!codegen->output) {
        fprintf(stderr, "Error: Could not open output file %s\n", 
                output_filename);
        free(codegen);
        return NULL;
    }
    
    codegen->current_function = NULL;
    codegen->stack_offset = 0;
    codegen->label_counter = 0;
    codegen->next_reg = 0;
    
    for (int i = 0; i < REG_COUNT; i++) {
        codegen->registers_used[i] = false;
    }
    
    return codegen;
}

void free_code_generator(CodeGenerator* codegen) {
    if (!codegen) return;
    if (codegen->output) {
        fclose(codegen->output);
    }
    free(codegen);
}

/*
 * TODO 2: Implement assembly emission helpers
 * 
 * Guidelines:
 * - Functions to emit assembly instructions
 * - Use fprintf to write to output file
 * - Add comments for readability
 */

// Emit a label
void emit_label(CodeGenerator* cg, const char* label) {
    fprintf(cg->output, "%s:\n", label);
}

// Emit an instruction with no operands
void emit_op(CodeGenerator* cg, const char* op) {
    fprintf(cg->output, "    %s\n", op);
}

// Emit an instruction with one operand
void emit_op1(CodeGenerator* cg, const char* op, const char* arg) {
    fprintf(cg->output, "    %s %s\n", op, arg);
}

// Emit an instruction with two operands
void emit_op2(CodeGenerator* cg, const char* op, const char* arg1, 
              const char* arg2) {
    fprintf(cg->output, "    %s %s, %s\n", op, arg1, arg2);
}

// Emit a comment
void emit_comment(CodeGenerator* cg, const char* comment) {
    fprintf(cg->output, "    # %s\n", comment);
}

// Generate unique label
char* generate_label(CodeGenerator* cg, const char* prefix) {
    // TODO: Generate unique label using label counter
    char* label = malloc(64);
    snprintf(label, 64, ".L%s_%d", prefix, cg->label_counter++);
    return label;
}

/*
 * TODO 3: Implement register allocation
 * 
 * Guidelines:
 * - Simple register allocator (just use next available register)
 * - Track which registers are in use
 * - Allocate and free registers
 * - Spill to stack if all registers used (advanced)
 */

// Allocate a register for temporary computation
Register allocate_register(CodeGenerator* cg) {
    // TODO: Find next available register
    // For simplicity, just use RAX, RCX, RDX, RBX in order
    for (int i = 0; i < 4; i++) {  // Only use first 4 general-purpose regs
        if (!cg->registers_used[i]) {
            cg->registers_used[i] = true;
            return (Register)i;
        }
    }
    
    fprintf(stderr, "Error: Out of registers (spilling not implemented)\n");
    return REG_RAX;  // Fallback
}

// Free a register after use
void free_register(CodeGenerator* cg, Register reg) {
    // TODO: Mark register as available
    cg->registers_used[reg] = false;
}

/*
 * TODO 4: Implement function prologue and epilogue
 * 
 * Guidelines:
 * - Prologue: save old %rbp, set up new frame pointer
 * - Allocate stack space for local variables
 * - Epilogue: restore stack pointer and base pointer, return
 */

// Emit function prologue
void emit_function_prologue(CodeGenerator* cg, const char* func_name, 
                             int local_space) {
    // TODO: Emit standard function prologue
    // 
    // pushq %rbp           # Save old frame pointer
    // movq %rsp, %rbp      # Set up new frame pointer
    // subq $N, %rsp        # Allocate space for locals (N must be 16-byte aligned)
    
    emit_comment(cg, "Function prologue");
    emit_op1(cg, "pushq", "%rbp");
    emit_op2(cg, "movq", "%rsp", "%rbp");
    
    // Align local space to 16-byte boundary
    if (local_space > 0) {
        int aligned_space = ((local_space + 15) / 16) * 16;
        char buf[32];
        snprintf(buf, sizeof(buf), "$%d", aligned_space);
        emit_op2(cg, "subq", buf, "%rsp");
    }
}

// Emit function epilogue
void emit_function_epilogue(CodeGenerator* cg) {
    // TODO: Emit standard function epilogue
    // 
    // movq %rbp, %rsp      # Restore stack pointer
    // popq %rbp            # Restore old frame pointer
    // ret                  # Return
    
    emit_comment(cg, "Function epilogue");
    emit_op2(cg, "movq", "%rbp", "%rsp");
    emit_op1(cg, "popq", "%rbp");
    emit_op(cg, "ret");
}

/*
 * TODO 5: Implement expression code generation
 * 
 * Guidelines:
 * - Generate code for each expression type
 * - Return the register containing the result
 * - Handle operator precedence (already done by parser)
 * - Emit appropriate assembly instructions
 */

// Forward declaration
Register generate_expression(CodeGenerator* cg, ASTNode* expr, 
                              CodeGenSymbolTable* symtab);

// Generate code for binary operation
Register generate_binary_op(CodeGenerator* cg, ASTNode* node, 
                             CodeGenSymbolTable* symtab) {
    // TODO: Generate code for binary operation
    // 1. Generate code for left operand (get register)
    // 2. Generate code for right operand (get register)
    // 3. Emit instruction for operation
    // 4. Free one of the registers
    // 5. Return register with result
    // 
    // Example for addition (a + b):
    //   # Generate left operand → %rax
    //   # Generate right operand → %rcx
    //   addq %rcx, %rax      # Add, result in %rax
    //   # Free %rcx
    //   # Return %rax
    // 
    // Operators:
    //   OP_ADD: addq
    //   OP_SUB: subq
    //   OP_MUL: imulq
    //   OP_DIV: idivq (more complex, needs setup)
    //   OP_EQ, OP_NE, OP_LT, OP_GT, OP_LE, OP_GE: cmp + setCC
    
    return REG_RAX;
}

// Generate code for unary operation
Register generate_unary_op(CodeGenerator* cg, ASTNode* node, 
                            CodeGenSymbolTable* symtab) {
    // TODO: Generate code for unary operation
    // 
    // OP_NEG (-): negq
    // OP_NOT (!): test + setCC
    // OP_ADDR (&): lea (load effective address)
    // OP_DEREF (*): movq (load from memory)
    
    return REG_RAX;
}

// Generate code for assignment
Register generate_assignment(CodeGenerator* cg, ASTNode* node, 
                              CodeGenSymbolTable* symtab) {
    // TODO: Generate code for assignment
    // 1. Generate code for right-hand side (value to assign)
    // 2. Get location of left-hand side (variable)
    // 3. Store value to that location
    // 4. Result is the assigned value
    // 
    // Example (x = 42):
    //   movq $42, %rax       # Right-hand side
    //   movq %rax, -8(%rbp)  # Store to x (at offset -8)
    
    return REG_RAX;
}

// Generate code for function call
Register generate_call(CodeGenerator* cg, ASTNode* node, 
                        CodeGenSymbolTable* symtab) {
    // TODO: Generate code for function call
    // 1. Generate code for each argument (reverse order for stack)
    // 2. Push arguments onto stack or use registers (x86-64 calling convention)
    // 3. Call the function
    // 4. Clean up stack if needed
    // 5. Result is in %rax
    // 
    // x86-64 calling convention:
    //   First 6 integer args in: %rdi, %rsi, %rdx, %rcx, %r8, %r9
    //   Rest on stack (push in reverse order)
    //   Return value in %rax
    
    return REG_RAX;
}

// Generate code for identifier (load variable)
Register generate_identifier(CodeGenerator* cg, ASTNode* node, 
                               CodeGenSymbolTable* symtab) {
    // TODO: Generate code to load variable into register
    // 1. Look up variable location in symbol table
    // 2. Allocate register
    // 3. Load from memory location
    // 
    // Example (load x):
    //   movq -8(%rbp), %rax  # Load x (at offset -8) into %rax
    
    return REG_RAX;
}

// Generate code for literal
Register generate_literal(CodeGenerator* cg, ASTNode* node, 
                           CodeGenSymbolTable* symtab) {
    // TODO: Generate code to load literal into register
    // 1. Allocate register
    // 2. Move immediate value into register
    // 
    // Example (load 42):
    //   movq $42, %rax       # Load immediate 42 into %rax
    
    Register reg = allocate_register(cg);
    char buf[64];
    snprintf(buf, sizeof(buf), "$%s", node->data.literal.value);
    emit_op2(cg, "movq", buf, register_names_64[reg]);
    return reg;
}

// Main expression code generation dispatcher
Register generate_expression(CodeGenerator* cg, ASTNode* expr, 
                              CodeGenSymbolTable* symtab) {
    if (!expr) return REG_RAX;
    
    // TODO: Dispatch to appropriate handler based on expr->type
    switch (expr->type) {
        case AST_BINARY_OP:
            return generate_binary_op(cg, expr, symtab);
        case AST_UNARY_OP:
            return generate_unary_op(cg, expr, symtab);
        case AST_ASSIGNMENT:
            return generate_assignment(cg, expr, symtab);
        case AST_CALL:
            return generate_call(cg, expr, symtab);
        case AST_IDENTIFIER:
            return generate_identifier(cg, expr, symtab);
        case AST_LITERAL:
            return generate_literal(cg, expr, symtab);
        default:
            fprintf(stderr, "Error: Unknown expression type in codegen\n");
            return REG_RAX;
    }
}

/*
 * TODO 6: Implement statement code generation
 * 
 * Guidelines:
 * - Generate code for each statement type
 * - Handle control flow (if, while, for)
 * - Use labels for jumps
 */

// Forward declaration
void generate_statement(CodeGenerator* cg, ASTNode* stmt, 
                         CodeGenSymbolTable* symtab);

// Generate code for return statement
void generate_return(CodeGenerator* cg, ASTNode* node, 
                      CodeGenSymbolTable* symtab) {
    // TODO: Generate code for return
    // 1. Generate code for return value expression
    // 2. Put result in %rax (return value register)
    // 3. Jump to function epilogue
}

// Generate code for if statement
void generate_if(CodeGenerator* cg, ASTNode* node, 
                  CodeGenSymbolTable* symtab) {
    // TODO: Generate code for if statement
    // 1. Generate unique labels for else and end
    // 2. Generate code for condition
    // 3. Test result and jump to else if false
    // 4. Generate code for then branch
    // 5. Jump to end
    // 6. Emit else label
    // 7. Generate code for else branch (if present)
    // 8. Emit end label
    // 
    // Example:
    //   <condition code>
    //   test %rax, %rax
    //   je .Lelse_1
    //   <then branch>
    //   jmp .Lend_1
    // .Lelse_1:
    //   <else branch>
    // .Lend_1:
}

// Generate code for while statement
void generate_while(CodeGenerator* cg, ASTNode* node, 
                     CodeGenSymbolTable* symtab) {
    // TODO: Generate code for while loop
    // 1. Generate unique labels for loop start and end
    // 2. Emit loop start label
    // 3. Generate code for condition
    // 4. Test and jump to end if false
    // 5. Generate code for body
    // 6. Jump back to loop start
    // 7. Emit end label
    // 
    // Example:
    // .Lloop_1:
    //   <condition code>
    //   test %rax, %rax
    //   je .Lend_1
    //   <body>
    //   jmp .Lloop_1
    // .Lend_1:
}

// Generate code for for statement
void generate_for(CodeGenerator* cg, ASTNode* node, 
                   CodeGenSymbolTable* symtab) {
    // TODO: Generate code for for loop
    // Similar to while but with init and increment
    //   <init>
    // .Lloop_1:
    //   <condition>
    //   test %rax, %rax
    //   je .Lend_1
    //   <body>
    //   <increment>
    //   jmp .Lloop_1
    // .Lend_1:
}

// Generate code for compound statement
void generate_compound(CodeGenerator* cg, ASTNode* node, 
                        CodeGenSymbolTable* symtab) {
    // TODO: Generate code for each statement in the block
    // Just iterate through statements and generate code for each
}

// Generate code for declaration
void generate_declaration(CodeGenerator* cg, ASTNode* node, 
                           CodeGenSymbolTable* symtab) {
    // TODO: Generate code for variable declaration
    // 1. Allocate space on stack for variable
    // 2. If initializer present, generate code and store
    // 3. Track variable location in symbol table
}

// Generate code for expression statement
void generate_expr_stmt(CodeGenerator* cg, ASTNode* node, 
                         CodeGenSymbolTable* symtab) {
    // TODO: Generate code for expression, discard result
    Register reg = generate_expression(cg, node->data.expr_stmt.expr, symtab);
    free_register(cg, reg);
}

// Main statement code generation dispatcher
void generate_statement(CodeGenerator* cg, ASTNode* stmt, 
                         CodeGenSymbolTable* symtab) {
    if (!stmt) return;
    
    // TODO: Dispatch based on statement type
    switch (stmt->type) {
        case AST_RETURN:
            generate_return(cg, stmt, symtab);
            break;
        case AST_IF:
            generate_if(cg, stmt, symtab);
            break;
        case AST_WHILE:
            generate_while(cg, stmt, symtab);
            break;
        case AST_FOR:
            generate_for(cg, stmt, symtab);
            break;
        case AST_COMPOUND:
            generate_compound(cg, stmt, symtab);
            break;
        case AST_DECLARATION:
            generate_declaration(cg, stmt, symtab);
            break;
        case AST_EXPR_STMT:
            generate_expr_stmt(cg, stmt, symtab);
            break;
        default:
            fprintf(stderr, "Error: Unknown statement type in codegen\n");
            break;
    }
}

/*
 * TODO 7: Implement function code generation
 * 
 * Guidelines:
 * - Emit function label
 * - Generate prologue
 * - Generate code for body
 * - Generate epilogue
 */
void generate_function(CodeGenerator* cg, ASTNode* func) {
    // TODO: Generate code for function
    // 1. Emit function label (.globl and label)
    // 2. Calculate stack space needed
    // 3. Generate prologue
    // 4. Generate code for body
    // 5. Generate epilogue
}

/*
 * TODO 8: Implement program code generation
 * 
 * Guidelines:
 * - Emit assembly header
 * - Generate code for each function
 * - Emit any necessary data sections
 */
void generate_program(CodeGenerator* cg, ASTNode* program) {
    // TODO: Generate code for entire program
    // 1. Emit assembly header/directives
    // 2. Iterate through functions and generate code
}

/*
 * Main code generation entry point
 */
bool generate_code(ASTNode* ast, const char* output_filename) {
    if (!ast) {
        fprintf(stderr, "Error: NULL AST passed to code generator\n");
        return false;
    }
    
    CodeGenerator* cg = create_code_generator(output_filename);
    if (!cg) return false;
    
    generate_program(cg, ast);
    
    printf("Code generation completed: %s\n", output_filename);
    
    free_code_generator(cg);
    return true;
}

/*
 * Test main (for standalone testing)
 */
int main(int argc, char** argv) {
    printf("Code generator template - implement the TODO sections\n");
    printf("This generator will produce x86-64 assembly code\n");
    
    // TODO: Integrate with semantic analyzer
    // Token** tokens = tokenize(source_code);
    // ASTNode* ast = parse(tokens);
    // if (semantic_analyze(ast)) {
    //     generate_code(ast, "output.s");
    //     // Can then assemble with: gcc output.s -o program
    // }
    // free_ast(ast);
    
    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Implement assembly emission helpers
 *         Test: emit simple instructions, labels
 * 
 * Step 2: Implement literal loading
 *         Test: movq $42, %rax
 * 
 * Step 3: Implement simple binary operations
 *         Test: addq, subq, imulq
 * 
 * Step 4: Implement variable access (load/store)
 *         Test: movq -8(%rbp), %rax
 * 
 * Step 5: Implement function prologue/epilogue
 *         Test: pushq/popq, stack frame
 * 
 * Step 6: Implement return statement
 *         Test: simple functions with return
 * 
 * Step 7: Implement control flow (if, while)
 *         Test: conditional jumps, loops
 * 
 * Step 8: Implement function calls
 *         Test: argument passing, call instruction
 * 
 * Testing Strategy:
 * - Start with simplest program: int main() { return 0; }
 * - Add arithmetic: int main() { return 2 + 3; }
 * - Add variables: int main() { int x = 5; return x; }
 * - Add control flow: if statements, loops
 * - Add function calls
 * - Assemble and run generated code: gcc output.s -o program && ./program
 * - Check return code: echo $?
 * 
 * x86-64 Assembly Reference:
 * - movq src, dst: Move 64-bit value
 * - addq src, dst: Add src to dst, store in dst
 * - subq src, dst: Subtract src from dst
 * - imulq src, dst: Multiply (signed)
 * - idivq divisor: Divide %rdx:%rax by divisor, quotient in %rax
 * - cmpq src, dst: Compare (sets flags)
 * - je label: Jump if equal
 * - jne label: Jump if not equal
 * - jl label: Jump if less
 * - jg label: Jump if greater
 * - jmp label: Unconditional jump
 * - call func: Call function
 * - ret: Return from function
 * - pushq src: Push onto stack
 * - popq dst: Pop from stack
 * 
 * Calling Convention (System V AMD64 ABI):
 * - Integer/pointer args 1-6: %rdi, %rsi, %rdx, %rcx, %r8, %r9
 * - Additional args on stack (push in reverse order)
 * - Return value in %rax
 * - Caller-saved: %rax, %rcx, %rdx, %rsi, %rdi, %r8-%r11
 * - Callee-saved: %rbx, %r12-%r15, %rbp
 * - Stack must be 16-byte aligned before call
 */
