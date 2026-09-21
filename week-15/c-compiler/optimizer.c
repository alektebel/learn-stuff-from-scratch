/*
 * Simple C Compiler - Optimizer Template
 * 
 * This template guides you through building an optimizer for C.
 * The optimizer performs transformations on the AST or IR to improve
 * code quality (speed, size, or both).
 * 
 * Common optimizations:
 * 1. Constant folding (evaluate constant expressions at compile time)
 * 2. Dead code elimination (remove unreachable code)
 * 3. Common subexpression elimination (CSE)
 * 4. Copy propagation (replace variable uses with their values)
 * 5. Algebraic simplifications (x * 1 → x, x + 0 → x, etc.)
 * 6. Strength reduction (x * 2 → x << 1)
 * 7. Loop optimizations (loop unrolling, loop-invariant code motion)
 * 
 * Compilation: gcc -o optimizer optimizer.c semantic.c parser.c lexer.c -I.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <limits.h>
#include "ast.h"

/*
 * Optimizer State
 * 
 * Tracks optimization statistics and state.
 */
typedef struct {
    int optimizations_applied;
    bool changed;                   // Did this pass change anything?
    int pass_count;                 // Number of optimization passes
} Optimizer;

/*
 * TODO 1: Implement optimizer initialization
 * 
 * Guidelines:
 * - Initialize statistics counters
 * - Set up any data structures needed
 */
Optimizer* create_optimizer() {
    Optimizer* opt = malloc(sizeof(Optimizer));
    opt->optimizations_applied = 0;
    opt->changed = false;
    opt->pass_count = 0;
    return opt;
}

void free_optimizer(Optimizer* opt) {
    free(opt);
}

/*
 * TODO 2: Implement constant folding
 * 
 * Guidelines:
 * - Evaluate constant expressions at compile time
 * - Replace expression nodes with literal nodes
 * - Handle arithmetic, logical, and relational operators
 * 
 * Examples:
 *   2 + 3       → 5
 *   10 * 0      → 0
 *   5 == 5      → 1 (true)
 *   x + 0       → x
 *   x * 1       → x
 *   x * 0       → 0
 */

// Check if node is a constant literal
bool is_constant(ASTNode* node) {
    return node && node->type == AST_LITERAL;
}

// Get integer value from literal node
bool get_constant_value(ASTNode* node, long* value) {
    if (!is_constant(node)) return false;
    
    // TODO: Parse the literal value string to integer
    *value = atol(node->data.literal.value);
    return true;
}

// Create a new literal node with given value
ASTNode* create_constant_node(long value, int line, int column) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%ld", value);
    return create_literal_node(buf, line, column);
}

// Fold constant binary operation
ASTNode* fold_binary_op(Optimizer* opt, ASTNode* node) {
    // TODO: Implement constant folding for binary operations
    // 1. Check if both operands are constants
    // 2. Evaluate the operation
    // 3. Return new literal node with result
    // 4. If not both constant, try algebraic simplifications
    
    ASTNode* left = node->data.binary.left;
    ASTNode* right = node->data.binary.right;
    
    long left_val, right_val;
    bool left_const = get_constant_value(left, &left_val);
    bool right_const = get_constant_value(right, &right_val);
    
    // Both operands are constants
    if (left_const && right_const) {
        long result = 0;
        bool can_fold = true;
        
        switch (node->data.binary.op) {
            case OP_ADD: result = left_val + right_val; break;
            case OP_SUB: result = left_val - right_val; break;
            case OP_MUL: result = left_val * right_val; break;
            case OP_DIV:
                if (right_val == 0) {
                    fprintf(stderr, "Warning: Division by zero at line %d\n", 
                            node->line);
                    can_fold = false;
                } else {
                    result = left_val / right_val;
                }
                break;
            case OP_MOD:
                if (right_val == 0) {
                    fprintf(stderr, "Warning: Modulo by zero at line %d\n", 
                            node->line);
                    can_fold = false;
                } else {
                    result = left_val % right_val;
                }
                break;
            case OP_EQ: result = (left_val == right_val); break;
            case OP_NE: result = (left_val != right_val); break;
            case OP_LT: result = (left_val < right_val); break;
            case OP_GT: result = (left_val > right_val); break;
            case OP_LE: result = (left_val <= right_val); break;
            case OP_GE: result = (left_val >= right_val); break;
            case OP_AND: result = (left_val && right_val); break;
            case OP_OR: result = (left_val || right_val); break;
            default: can_fold = false; break;
        }
        
        if (can_fold) {
            opt->optimizations_applied++;
            opt->changed = true;
            return create_constant_node(result, node->line, node->column);
        }
    }
    
    // TODO: Algebraic simplifications
    // x + 0 → x
    // 0 + x → x
    // x * 0 → 0
    // 0 * x → 0
    // x * 1 → x
    // 1 * x → x
    // x - 0 → x
    // x / 1 → x
    
    return node;
}

// Fold constant unary operation
ASTNode* fold_unary_op(Optimizer* opt, ASTNode* node) {
    // TODO: Implement constant folding for unary operations
    // -5 → -5
    // !0 → 1
    // !1 → 0
    
    return node;
}

/*
 * TODO 3: Implement dead code elimination
 * 
 * Guidelines:
 * - Remove statements after return statements in same block
 * - Remove unreachable if branches (if (0) { ... })
 * - Remove unused variable declarations (advanced)
 * 
 * Examples:
 *   return 0;
 *   x = 5;          ← Dead code (never executed)
 * 
 *   if (0) {
 *       ...         ← Dead code (condition always false)
 *   }
 */

bool is_constant_zero(ASTNode* node) {
    long value;
    return get_constant_value(node, &value) && value == 0;
}

bool is_constant_nonzero(ASTNode* node) {
    long value;
    return get_constant_value(node, &value) && value != 0;
}

// Remove dead code from compound statement
ASTNode* eliminate_dead_code_compound(Optimizer* opt, ASTNode* compound) {
    // TODO: Implement dead code elimination in compound statements
    // 1. Iterate through statements
    // 2. If we encounter a return, mark all following statements as dead
    // 3. Remove dead statements
    
    return compound;
}

// Eliminate dead branches in if statement
ASTNode* eliminate_dead_code_if(Optimizer* opt, ASTNode* if_stmt) {
    // TODO: Implement dead code elimination for if statements
    // If condition is constant:
    //   - if (1) { A } else { B } → A
    //   - if (0) { A } else { B } → B
    
    if (is_constant_nonzero(if_stmt->data.if_stmt.condition)) {
        // Condition always true, keep only then branch
        opt->optimizations_applied++;
        opt->changed = true;
        return if_stmt->data.if_stmt.then_branch;
    }
    
    if (is_constant_zero(if_stmt->data.if_stmt.condition)) {
        // Condition always false, keep only else branch (if any)
        opt->optimizations_applied++;
        opt->changed = true;
        if (if_stmt->data.if_stmt.else_branch) {
            return if_stmt->data.if_stmt.else_branch;
        } else {
            // No else branch, entire if statement is dead
            return NULL;
        }
    }
    
    return if_stmt;
}

// Eliminate dead code in while loop
ASTNode* eliminate_dead_code_while(Optimizer* opt, ASTNode* while_stmt) {
    // TODO: Implement dead code elimination for while loops
    // If condition is constant 0, entire loop is dead
    
    if (is_constant_zero(while_stmt->data.while_stmt.condition)) {
        opt->optimizations_applied++;
        opt->changed = true;
        return NULL;  // Remove the loop
    }
    
    return while_stmt;
}

/*
 * TODO 4: Implement copy propagation
 * 
 * Guidelines:
 * - Track simple assignments (x = y)
 * - Replace uses of x with y when possible
 * - Invalidate when variable is reassigned
 * 
 * Example:
 *   x = y;
 *   z = x + 1;  → z = y + 1;
 */

// This is more complex and typically requires dataflow analysis
// Simplified version for demonstration:

typedef struct CopyInfo {
    char* var;
    char* copy;
    struct CopyInfo* next;
} CopyInfo;

ASTNode* propagate_copies_expr(ASTNode* expr, CopyInfo* copies) {
    // TODO: Implement copy propagation in expressions
    // Replace variable references with their copied values
    
    return expr;
}

/*
 * TODO 5: Implement strength reduction
 * 
 * Guidelines:
 * - Replace expensive operations with cheaper ones
 * - x * 2 → x << 1 (shift is faster than multiply)
 * - x * 1 → x
 * - x / 2 → x >> 1 (for positive integers)
 * 
 * This is architecture-dependent and may not always be beneficial.
 */

ASTNode* strength_reduce_binary_op(Optimizer* opt, ASTNode* node) {
    // TODO: Implement strength reduction
    // Check for multiplications/divisions by powers of 2
    // Replace with shifts if appropriate
    
    return node;
}

/*
 * TODO 6: Implement optimization passes
 * 
 * Guidelines:
 * - Traverse AST and apply optimizations
 * - Run multiple passes until no changes
 * - Order matters: some optimizations enable others
 */

// Forward declarations
ASTNode* optimize_expression(Optimizer* opt, ASTNode* expr);
ASTNode* optimize_statement(Optimizer* opt, ASTNode* stmt);

// Optimize expression
ASTNode* optimize_expression(Optimizer* opt, ASTNode* expr) {
    if (!expr) return NULL;
    
    // TODO: Recursively optimize expression tree
    switch (expr->type) {
        case AST_BINARY_OP:
            // Optimize operands first
            expr->data.binary.left = optimize_expression(opt, 
                                                         expr->data.binary.left);
            expr->data.binary.right = optimize_expression(opt, 
                                                          expr->data.binary.right);
            // Then try to fold the operation
            return fold_binary_op(opt, expr);
            
        case AST_UNARY_OP:
            expr->data.unary.operand = optimize_expression(opt, 
                                                           expr->data.unary.operand);
            return fold_unary_op(opt, expr);
            
        case AST_ASSIGNMENT:
            expr->data.assignment.lhs = optimize_expression(opt, 
                                                            expr->data.assignment.lhs);
            expr->data.assignment.rhs = optimize_expression(opt, 
                                                            expr->data.assignment.rhs);
            return expr;
            
        case AST_CALL:
            // Optimize arguments
            // TODO: Recursively optimize argument list
            return expr;
            
        case AST_IDENTIFIER:
        case AST_LITERAL:
            // Nothing to optimize
            return expr;
            
        default:
            return expr;
    }
}

// Optimize statement
ASTNode* optimize_statement(Optimizer* opt, ASTNode* stmt) {
    if (!stmt) return NULL;
    
    // TODO: Recursively optimize statement tree
    switch (stmt->type) {
        case AST_RETURN:
            stmt->data.ret.expr = optimize_expression(opt, stmt->data.ret.expr);
            return stmt;
            
        case AST_IF:
            stmt->data.if_stmt.condition = optimize_expression(opt, 
                                                               stmt->data.if_stmt.condition);
            stmt->data.if_stmt.then_branch = optimize_statement(opt, 
                                                                stmt->data.if_stmt.then_branch);
            stmt->data.if_stmt.else_branch = optimize_statement(opt, 
                                                                stmt->data.if_stmt.else_branch);
            return eliminate_dead_code_if(opt, stmt);
            
        case AST_WHILE:
            stmt->data.while_stmt.condition = optimize_expression(opt, 
                                                                  stmt->data.while_stmt.condition);
            stmt->data.while_stmt.body = optimize_statement(opt, 
                                                            stmt->data.while_stmt.body);
            return eliminate_dead_code_while(opt, stmt);
            
        case AST_FOR:
            // TODO: Optimize for loop
            return stmt;
            
        case AST_COMPOUND:
            // TODO: Optimize each statement in compound
            // Handle dead code elimination
            return eliminate_dead_code_compound(opt, stmt);
            
        case AST_DECLARATION:
            stmt->data.declaration.initializer = optimize_expression(opt, 
                                                                     stmt->data.declaration.initializer);
            return stmt;
            
        case AST_EXPR_STMT:
            stmt->data.expr_stmt.expr = optimize_expression(opt, 
                                                            stmt->data.expr_stmt.expr);
            return stmt;
            
        default:
            return stmt;
    }
}

// Optimize function
void optimize_function(Optimizer* opt, ASTNode* func) {
    if (!func || func->type != AST_FUNCTION) return;
    
    // TODO: Optimize function body
    func->data.function.body = optimize_statement(opt, func->data.function.body);
}

// Optimize program
void optimize_program(Optimizer* opt, ASTNode* program) {
    if (!program || program->type != AST_PROGRAM) return;
    
    // TODO: Optimize each function
    ASTNode* func = program->data.program.functions;
    while (func) {
        optimize_function(opt, func);
        func = func->next;
    }
}

/*
 * Main optimization entry point
 * 
 * Runs multiple optimization passes until convergence (no more changes).
 */
bool optimize(ASTNode* ast, int max_passes) {
    if (!ast) {
        fprintf(stderr, "Error: NULL AST passed to optimizer\n");
        return false;
    }
    
    Optimizer* opt = create_optimizer();
    
    // Run optimization passes until no changes or max passes reached
    for (int pass = 0; pass < max_passes; pass++) {
        opt->changed = false;
        opt->pass_count++;
        
        optimize_program(opt, ast);
        
        if (!opt->changed) {
            // No changes in this pass, we've converged
            break;
        }
    }
    
    printf("Optimization completed:\n");
    printf("  Passes: %d\n", opt->pass_count);
    printf("  Optimizations applied: %d\n", opt->optimizations_applied);
    
    free_optimizer(opt);
    return true;
}

/*
 * Test main (for standalone testing)
 */
int main(int argc, char** argv) {
    printf("Optimizer template - implement the TODO sections\n");
    printf("This optimizer will improve code quality\n");
    
    // TODO: Integrate with parser and semantic analyzer
    // Token** tokens = tokenize(source_code);
    // ASTNode* ast = parse(tokens);
    // if (semantic_analyze(ast)) {
    //     optimize(ast, 10);  // Run up to 10 optimization passes
    //     generate_code(ast, "output.s");
    // }
    // free_ast(ast);
    
    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Implement constant folding for arithmetic operations
 *         Test: 2 + 3 → 5, 10 * 2 → 20
 * 
 * Step 2: Implement algebraic simplifications
 *         Test: x + 0 → x, x * 1 → x, x * 0 → 0
 * 
 * Step 3: Implement constant folding for comparisons
 *         Test: 5 > 3 → 1, 10 == 5 → 0
 * 
 * Step 4: Implement dead code elimination for if statements
 *         Test: if (0) { ... } → (removed)
 * 
 * Step 5: Implement dead code elimination for compound statements
 *         Test: return 0; x = 5; → return 0;
 * 
 * Step 6: Implement strength reduction
 *         Test: x * 2 → x << 1
 * 
 * Step 7: Implement copy propagation (advanced)
 *         Test: x = y; z = x; → x = y; z = y;
 * 
 * Testing Strategy:
 * - Create test programs with obvious optimization opportunities
 * - Run optimizer and inspect optimized AST
 * - Compare generated code before and after optimization
 * - Measure code size and execution speed improvements
 * - Ensure correctness (optimized code behaves identically)
 * 
 * Common Pitfalls:
 * - Removing code that has side effects
 * - Not handling overflow in constant folding
 * - Breaking semantics with aggressive optimizations
 * - Not considering aliasing in copy propagation
 * - Memory leaks when replacing AST nodes
 * 
 * Advanced Optimizations (Extensions):
 * - Common subexpression elimination (CSE)
 * - Loop optimizations:
 *   - Loop unrolling
 *   - Loop-invariant code motion
 *   - Induction variable elimination
 * - Inline small functions
 * - Tail call optimization
 * - Register allocation improvements
 * - Peephole optimization (on assembly code)
 * 
 * Optimization Order:
 * Good order for optimization passes:
 * 1. Constant folding
 * 2. Copy propagation
 * 3. Dead code elimination
 * 4. Strength reduction
 * 5. Repeat until convergence
 * 
 * Resources:
 * - "Engineering a Compiler" by Cooper & Torczon (Chapter 8-10)
 * - "Compilers: Principles, Techniques, and Tools" (Dragon Book, Chapter 9)
 * - "Modern Compiler Implementation in C" by Appel (Chapter 19-20)
 */
