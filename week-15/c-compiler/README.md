# C Compiler Implementation

A complete from-scratch implementation of a C compiler written in C. This project breaks down compiler construction into clear, manageable phases with extensive documentation and implementation templates.

## Goal

Build a fully functional C compiler to deeply understand:
- **Lexical analysis**: Breaking source code into tokens
- **Syntax analysis**: Building Abstract Syntax Trees (AST)
- **Semantic analysis**: Type checking and validation
- **Code generation**: Producing x86-64 assembly
- **Optimization**: Improving code quality

## Project Structure

```
c-compiler/
├── README.md                   # This file
├── IMPLEMENTATION_GUIDE.md     # Detailed step-by-step implementation guide
├── Makefile                    # Build system for all compiler phases
├── ast.h                       # AST node definitions and structures
├── lexer.c                     # Lexical analyzer (tokenization)
├── parser.c                    # Syntax analyzer (parsing)
├── semantic.c                  # Semantic analyzer (type checking)
├── codegen.c                   # Code generator (assembly output)
├── optimizer.c                 # Optimizer (code improvement)
├── tests/                      # Test programs and test suite
└── solutions/                  # Complete reference implementations
    ├── README.md
    ├── lexer.c
    ├── parser.c
    └── ...
```

## Features

### Supported C Subset

Our compiler supports a meaningful subset of C:

**Data Types**:
- `int`, `char`, `void`
- Pointers (`int*`, `char*`, etc.)
- Arrays (basic support)

**Control Flow**:
- `if` / `else` statements
- `while` loops
- `for` loops
- `return` statements

**Operators**:
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `&&`, `||`, `!`
- Assignment: `=`
- Unary: `-`, `!`, `&` (address-of), `*` (dereference)

**Functions**:
- Function definitions
- Function calls
- Parameters and arguments
- Return values

**Variables**:
- Local and global variables
- Scoped declarations
- Variable initialization

### Compiler Phases

#### 1. Lexer (Tokenization)
- **File**: `lexer.c`
- **Input**: C source code (string)
- **Output**: Array of tokens
- **Features**:
  - Keyword recognition
  - Identifier handling
  - Number literals
  - Operator recognition
  - Multi-character operators (`==`, `!=`, etc.)
  - Position tracking (line/column)

#### 2. Parser (Syntax Analysis)
- **File**: `parser.c`
- **Input**: Token array
- **Output**: Abstract Syntax Tree (AST)
- **Features**:
  - Recursive descent parsing
  - Operator precedence handling
  - Error recovery
  - Full C grammar support (for our subset)

#### 3. Semantic Analyzer (Type Checking)
- **File**: `semantic.c`
- **Input**: AST
- **Output**: Type-annotated AST
- **Features**:
  - Symbol table management
  - Scope handling
  - Type checking
  - Function signature validation
  - Variable declaration checking

#### 4. Code Generator (Assembly Output)
- **File**: `codegen.c`
- **Input**: Type-checked AST
- **Output**: x86-64 assembly code
- **Features**:
  - Function prologue/epilogue
  - Register allocation (simplified)
  - Stack frame management
  - Expression evaluation
  - Control flow translation
  - x86-64 calling convention

#### 5. Optimizer (Code Improvement)
- **File**: `optimizer.c`
- **Input**: AST
- **Output**: Optimized AST
- **Features**:
  - Constant folding
  - Dead code elimination
  - Algebraic simplifications
  - Copy propagation
  - Strength reduction

## Quick Start

### Prerequisites

- GCC or Clang compiler
- Make build system
- Basic understanding of C programming

### Building

Build individual phases:
```bash
make lexer      # Build lexer only
make parser     # Build parser (includes lexer)
make semantic   # Build semantic analyzer
make codegen    # Build code generator
make optimizer  # Build optimizer
```

Build everything:
```bash
make all        # Build all compiler phases
```

### Testing

Run tests for each phase:
```bash
make test-lexer     # Test lexer
make test-parser    # Test parser
make test           # Run all tests
```

### Usage Example

#### Step 1: Create a test program

`test.c`:
```c
int main() {
    int x = 5;
    int y = 10;
    return x + y;
}
```

#### Step 2: Compile through phases

```bash
# Tokenize
./lexer test.c

# Parse (build AST)
./parser test.c

# Type check
./semantic test.c

# Generate assembly
./codegen test.c -o output.s

# Assemble and link
gcc output.s -o program

# Run
./program
echo $?  # Should print 15
```

## Learning Path

### Phase 1: Lexical Analysis (1-2 hours)
**Goal**: Break source code into tokens

1. Read `lexer.c` template
2. Implement token types
3. Implement `is_keyword()` function
4. Implement `get_next_token()` for simple tokens
5. Add number and identifier recognition
6. Add multi-character operators
7. Test with sample programs

**Skills learned**:
- String processing
- Character classification
- State machines
- Pattern recognition

### Phase 2: Syntax Analysis (3-4 hours)
**Goal**: Build an Abstract Syntax Tree

1. Study `ast.h` for node structures
2. Read `parser.c` template
3. Implement token access functions
4. Implement primary expression parsing
5. Implement binary operators with precedence
6. Implement statement parsing
7. Implement function parsing
8. Test with complete programs

**Skills learned**:
- Recursive descent parsing
- Grammar rules
- Tree structures
- Operator precedence

### Phase 3: Semantic Analysis (2-3 hours)
**Goal**: Validate program semantics

1. Read `semantic.c` template
2. Implement symbol table (hash table)
3. Implement scope management
4. Implement type checking for expressions
5. Implement declaration checking
6. Implement function call validation
7. Test with valid and invalid programs

**Skills learned**:
- Symbol tables
- Scoping rules
- Type systems
- Error detection

### Phase 4: Code Generation (3-4 hours)
**Goal**: Produce assembly code

1. Read `codegen.c` template
2. Learn x86-64 basics
3. Implement function prologue/epilogue
4. Implement expression code generation
5. Implement statement code generation
6. Implement control flow
7. Test by assembling and running

**Skills learned**:
- Assembly language
- Calling conventions
- Register allocation
- Stack management

### Phase 5: Optimization (2-3 hours)
**Goal**: Improve code quality

1. Read `optimizer.c` template
2. Implement constant folding
3. Implement dead code elimination
4. Implement algebraic simplifications
5. Implement multi-pass optimization
6. Measure improvements

**Skills learned**:
- Code optimization techniques
- AST transformations
- Performance analysis

**Total Time**: ~12-16 hours for complete implementation

## Documentation

### Comprehensive Guides

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)**: Step-by-step implementation instructions with code examples, testing strategies, and debugging tips
- **Template Files**: Each `.c` file contains extensive TODO comments and guidelines
- **AST Header**: `ast.h` documents all node types and structures

### Additional Resources

**Books**:
- "Compilers: Principles, Techniques, and Tools" (Dragon Book)
- "Engineering a Compiler" by Cooper & Torczon
- "Modern Compiler Implementation in C" by Appel

**Online**:
- [Stanford CS143](https://web.stanford.edu/class/cs143/): Compilers course
- [x86-64 ABI Documentation](https://github.com/hjl-tools/x86-psABI/wiki/x86-64-psABI-1.0.pdf)
- [GNU Assembler Manual](https://sourceware.org/binutils/docs/as/)

**Video Courses**:
- [CS143 - Compilers - Stanford](https://web.stanford.edu/class/cs143/)
- [CS 6120 - Advanced Compilers - Cornell](https://www.cs.cornell.edu/courses/cs6120/2020fa/)
- [More compiler and programming language courses](https://github.com/Developer-Y/cs-video-courses#theoretical-cs-and-programming-languages)

## Testing

### Test Suite

Create tests in `tests/` directory:

```bash
# Arithmetic tests
tests/test_arithmetic.c

# Control flow tests
tests/test_if_else.c
tests/test_loops.c

# Function tests
tests/test_functions.c

# Error cases
tests/test_errors.c
```

### Automated Testing

Run the test suite:
```bash
make test
```

### Manual Testing

Test individual programs:
```bash
# Test your compiler
./codegen program.c -o output.s
gcc output.s -o program
./program

# Compare with GCC
gcc program.c -o gcc_program
./gcc_program

# Results should match
```

## Architecture

### Data Flow

```
┌─────────────┐
│ Source Code │
│   (*.c)     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Lexer     │ ← lexer.c
│ (Tokenizer) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Tokens    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Parser    │ ← parser.c
│   (Syntax)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     AST     │ ← ast.h
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Semantic   │ ← semantic.c
│   Analyzer  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Type-checked│
│     AST     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Optimizer  │ ← optimizer.c
│ (Optional)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Optimized  │
│     AST     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Code      │ ← codegen.c
│  Generator  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Assembly   │
│   (*.s)     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Assembler/ │ ← GCC/Clang
│   Linker    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Executable  │
└─────────────┘
```

## Advanced Topics

After completing the basic compiler, explore:

### Language Features
- Arrays (multi-dimensional)
- Structures and unions
- Typedef
- Enums
- Function pointers
- Strings and string literals
- Floating-point numbers

### Optimization Techniques
- Common subexpression elimination (CSE)
- Loop optimizations (unrolling, invariant code motion)
- Inlining
- Register allocation (graph coloring)
- Peephole optimization

### Advanced Code Generation
- Target different architectures (ARM, RISC-V)
- Generate LLVM IR
- Add debugging information (DWARF)
- Position-independent code (PIC)

### Error Handling
- Better error messages
- Error recovery
- Warnings
- Static analysis

### Tooling
- Add preprocessor (#include, #define)
- Create IDE integration
- Build debugging tools
- Add profiling support

## Troubleshooting

### Common Issues

**Segmentation Fault**:
- Check NULL pointer dereferences
- Verify memory allocation
- Use Valgrind: `valgrind ./compiler test.c`

**Parse Errors**:
- Print tokens to debug
- Check operator precedence
- Verify grammar rules

**Type Errors**:
- Print symbol table
- Check scope levels
- Trace type propagation

**Assembly Errors**:
- Check generated assembly
- Verify register usage
- Test with simpler programs

**Linker Errors**:
- Ensure `main` function exists
- Check function name mangling
- Verify calling convention

## Contributing

This is a learning project. Feel free to:
- Add more test cases
- Improve error messages
- Add language features
- Optimize existing code
- Fix bugs

## License

Educational purposes. Use freely for learning.

## Acknowledgments

Inspired by:
- Compiler courses at Stanford, MIT, and other universities
- LLVM and GCC compiler projects
- "Let's Build a Compiler" by Jack Crenshaw
- The Dragon Book authors

## Sources

- Aho, Lam, Sethi & Ullman, **Compilers: Principles, Techniques, and Tools** — the Dragon Book. Chapters 3–6 are this directory.
- Sandler, **Writing a C Compiler**, 2024 — the closest thing to a walk-through of exactly this project.
- Poletto & Sarkar, **"Linear Scan Register Allocation"**, TOPLAS 1999 — the allocator and its spilling, which is what `codegen.c` implements.
- Appel, **Modern Compiler Implementation in C** — if you want the intermediate representation treated properly.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-15--compilers)
