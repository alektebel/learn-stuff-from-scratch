# Tiny CUDA Compiler – Makefile
# Builds the compiler that translates CUDA kernels to PTX assembly.

CC      = gcc
CFLAGS  = -Wall -Wextra -std=c99 -O2
SRCS    = main.c lexer.c parser.c codegen.c
TARGET  = cuda_compiler

.PHONY: all clean test test-verbose help

all: $(TARGET)

$(TARGET): $(SRCS) lexer.h ast.h
	$(CC) $(CFLAGS) -o $@ $(SRCS)

# ── Tests ────────────────────────────────────────────────────────────────

test: $(TARGET)
	@echo "=== Running tiny CUDA compiler tests ==="
	@echo ""
	@echo "--- Test 1: vector_add kernel ---"
	@./$(TARGET) tests/vector_add.cu -o /tmp/vector_add.ptx && \
		echo "PTX output:" && cat /tmp/vector_add.ptx && echo "PASS" || echo "FAIL"
	@echo ""
	@echo "--- Test 2: matrix_add kernel ---"
	@./$(TARGET) tests/matrix_add.cu -o /tmp/matrix_add.ptx && \
		echo "PTX output:" && cat /tmp/matrix_add.ptx && echo "PASS" || echo "FAIL"
	@echo ""
	@echo "--- Test 3: multi-kernel file ---"
	@./$(TARGET) tests/multi_kernel.cu -o /tmp/multi_kernel.ptx && \
		echo "PTX output:" && cat /tmp/multi_kernel.ptx && echo "PASS" || echo "FAIL"

test-verbose: $(TARGET)
	@echo "=== Token dump: vector_add.cu ==="
	@./$(TARGET) tests/vector_add.cu -tokens
	@echo ""
	@echo "=== PTX output: vector_add.cu ==="
	@./$(TARGET) tests/vector_add.cu

# ── Validate PTX with ptxas if available ─────────────────────────────────
validate: test
	@if command -v ptxas > /dev/null 2>&1; then \
		echo "=== Validating PTX with ptxas ==="; \
		ptxas -arch sm_60 /tmp/vector_add.ptx -o /dev/null && echo "vector_add.ptx: OK"; \
		ptxas -arch sm_60 /tmp/matrix_add.ptx  -o /dev/null && echo "matrix_add.ptx: OK"; \
	else \
		echo "(ptxas not found – skipping PTX validation)"; \
	fi

clean:
	rm -f $(TARGET) *.o /tmp/vector_add.ptx /tmp/matrix_add.ptx /tmp/multi_kernel.ptx

help:
	@echo "Tiny CUDA Compiler – Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all           Build the compiler (default)"
	@echo "  test          Build and run all tests"
	@echo "  test-verbose  Show token dump + PTX for vector_add"
	@echo "  validate      Run tests and validate PTX with ptxas"
	@echo "  clean         Remove build artefacts"
	@echo ""
	@echo "Usage after building:"
	@echo "  ./cuda_compiler <input.cu> [-o output.ptx] [-arch sm_XX] [-tokens]"
	@echo ""
	@echo "Examples:"
	@echo "  ./cuda_compiler tests/vector_add.cu"
	@echo "  ./cuda_compiler tests/vector_add.cu -o out.ptx -arch sm_86"
	@echo "  ./cuda_compiler tests/vector_add.cu -tokens"
