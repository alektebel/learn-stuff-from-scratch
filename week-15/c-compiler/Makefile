# Makefile for C Compiler
# This builds each phase of the compiler separately for educational purposes

CC = gcc
CFLAGS = -Wall -Wextra -g -I.
TARGETS = lexer parser semantic codegen optimizer

# Build all compiler phases
all: $(TARGETS)

# Lexer - Tokenization phase
lexer: lexer.c
	$(CC) $(CFLAGS) -o lexer lexer.c
	@echo "Built: lexer"

# Parser - Syntax analysis phase (requires lexer)
parser: parser.c lexer.c ast.h
	$(CC) $(CFLAGS) -o parser parser.c lexer.c
	@echo "Built: parser"

# Semantic analyzer - Type checking and validation (requires parser)
semantic: semantic.c parser.c lexer.c ast.h
	$(CC) $(CFLAGS) -o semantic semantic.c parser.c lexer.c
	@echo "Built: semantic"

# Code generator - Assembly generation (requires semantic)
codegen: codegen.c semantic.c parser.c lexer.c ast.h
	$(CC) $(CFLAGS) -o codegen codegen.c semantic.c parser.c lexer.c
	@echo "Built: codegen"

# Optimizer - Code optimization (requires semantic)
optimizer: optimizer.c semantic.c parser.c lexer.c ast.h
	$(CC) $(CFLAGS) -o optimizer optimizer.c semantic.c parser.c lexer.c
	@echo "Built: optimizer"

# Clean all build artifacts
clean:
	rm -f $(TARGETS) *.o *.s
	@echo "Cleaned build artifacts"

# Run tests for each phase
test-lexer: lexer
	@echo "=== Testing Lexer ==="
	./lexer

test-parser: parser
	@echo "=== Testing Parser ==="
	./parser

test-semantic: semantic
	@echo "=== Testing Semantic Analyzer ==="
	./semantic

test-codegen: codegen
	@echo "=== Testing Code Generator ==="
	./codegen

test-optimizer: optimizer
	@echo "=== Testing Optimizer ==="
	./optimizer

# Run all tests
test: test-lexer test-parser test-semantic test-codegen test-optimizer

# Help target
help:
	@echo "C Compiler Makefile"
	@echo "==================="
	@echo ""
	@echo "Targets:"
	@echo "  all         - Build all compiler phases"
	@echo "  lexer       - Build lexer (tokenization)"
	@echo "  parser      - Build parser (syntax analysis)"
	@echo "  semantic    - Build semantic analyzer (type checking)"
	@echo "  codegen     - Build code generator (assembly generation)"
	@echo "  optimizer   - Build optimizer (code optimization)"
	@echo "  clean       - Remove all build artifacts"
	@echo "  test        - Run all tests"
	@echo "  test-*      - Run specific phase test"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Example workflow:"
	@echo "  make lexer && ./lexer        # Test lexer"
	@echo "  make parser && ./parser      # Test parser"
	@echo "  make all                     # Build everything"
	@echo "  make test                    # Run all tests"

.PHONY: all clean test test-lexer test-parser test-semantic test-codegen test-optimizer help
