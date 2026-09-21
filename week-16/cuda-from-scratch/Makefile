# Makefile for CUDA Learning Examples
# Builds all CUDA examples from basic to advanced

NVCC = nvcc
NVCC_FLAGS = -arch=sm_60 -O2
CUDA_LIBS = -lcudart

# Detect CUDA compute capability (optional, falls back to sm_60)
# You can override this: make ARCH=sm_75
ARCH ?= sm_60

# Compiler flags
CFLAGS = -arch=$(ARCH) -O2 -lineinfo
DEBUG_FLAGS = -g -G

# All example programs
EXAMPLES = 01_vector_addition \
           02_matrix_addition \
           03_matrix_multiplication \
           04_reduction \
           05_convolution \
           06_neural_network_forward \
           07_neural_network_backward \
           08_complete_neural_network

# Test programs
TESTS = tests/test_vector_addition \
        tests/test_matrix_operations \
        tests/test_neural_network

.PHONY: all clean test help examples

# Default target
all: examples

# Build all examples
examples: $(EXAMPLES)

# Build individual examples
01_vector_addition: 01_vector_addition.cu
	$(NVCC) $(CFLAGS) $< -o $@

02_matrix_addition: 02_matrix_addition.cu
	$(NVCC) $(CFLAGS) $< -o $@

03_matrix_multiplication: 03_matrix_multiplication.cu
	$(NVCC) $(CFLAGS) $< -o $@

04_reduction: 04_reduction.cu
	$(NVCC) $(CFLAGS) $< -o $@

05_convolution: 05_convolution.cu
	$(NVCC) $(CFLAGS) $< -o $@

06_neural_network_forward: 06_neural_network_forward.cu
	$(NVCC) $(CFLAGS) $< -o $@

07_neural_network_backward: 07_neural_network_backward.cu
	$(NVCC) $(CFLAGS) $< -o $@

08_complete_neural_network: 08_complete_neural_network.cu
	$(NVCC) $(CFLAGS) $< -o $@

# Convenience targets
vector_add: 01_vector_addition
matrix_add: 02_matrix_addition
matrix_mul: 03_matrix_multiplication
reduction: 04_reduction
conv: 05_convolution
nn_forward: 06_neural_network_forward
nn_backward: 07_neural_network_backward
neural_net: 08_complete_neural_network

# Build tests
tests: $(TESTS)

tests/test_vector_addition: tests/test_vector_addition.cu
	$(NVCC) $(CFLAGS) $< -o $@

tests/test_matrix_operations: tests/test_matrix_operations.cu
	$(NVCC) $(CFLAGS) $< -o $@

tests/test_neural_network: tests/test_neural_network.cu
	$(NVCC) $(CFLAGS) $< -o $@

# Run tests
test: tests
	@echo "Running vector addition tests..."
	@./tests/test_vector_addition || echo "Test failed"
	@echo ""
	@echo "Running matrix operations tests..."
	@./tests/test_matrix_operations || echo "Test failed"
	@echo ""
	@echo "Running neural network tests..."
	@./tests/test_neural_network || echo "Test failed"

# Run individual test targets
test-vector: tests/test_vector_addition
	@./tests/test_vector_addition

test-matrix: tests/test_matrix_operations
	@./tests/test_matrix_operations

test-nn: tests/test_neural_network
	@./tests/test_neural_network

# Build with debug information
debug: CFLAGS = $(DEBUG_FLAGS)
debug: all

# Run examples with default parameters
run-01: 01_vector_addition
	@./01_vector_addition 1000000

run-02: 02_matrix_addition
	@./02_matrix_addition 1024 1024

run-03: 03_matrix_multiplication
	@./03_matrix_multiplication 1024 1024 1024

run-04: 04_reduction
	@./04_reduction 1000000

run-05: 05_convolution
	@./05_convolution 512 512 5

run-06: 06_neural_network_forward
	@./06_neural_network_forward 100

run-07: 07_neural_network_backward
	@./07_neural_network_backward 100

run-08: 08_complete_neural_network
	@./08_complete_neural_network

# Benchmark mode
benchmark: all
	@echo "=== CUDA Performance Benchmarks ==="
	@echo ""
	@echo "1. Vector Addition (10M elements):"
	@./01_vector_addition 10000000
	@echo ""
	@echo "2. Matrix Addition (2048x2048):"
	@./02_matrix_addition 2048 2048
	@echo ""
	@echo "3. Matrix Multiplication (1024x1024):"
	@./03_matrix_multiplication 1024 1024 1024
	@echo ""
	@echo "4. Reduction (10M elements):"
	@./04_reduction 10000000
	@echo ""
	@echo "5. Convolution (1024x1024, 11x11 filter):"
	@./05_convolution 1024 1024 11

# Profile with nvprof (legacy) or ncu (modern)
profile-%: %
	@echo "Profiling $<..."
	@if command -v ncu > /dev/null; then \
		ncu --set full -o profile_$< ./$<; \
	else \
		nvprof ./$<; \
	fi

# Check CUDA installation
check-cuda:
	@echo "Checking CUDA installation..."
	@nvcc --version || echo "ERROR: nvcc not found"
	@nvidia-smi || echo "ERROR: nvidia-smi not found"

# Build solutions
solutions:
	@$(MAKE) -C solutions all

# Clean build artifacts
clean:
	rm -f $(EXAMPLES) $(TESTS)
	rm -f *.o
	rm -f tests/*.o
	rm -f profile_*
	rm -f *.nsys-rep *.sqlite

# Deep clean (including solution builds)
distclean: clean
	@$(MAKE) -C solutions clean

# Help target
help:
	@echo "CUDA Learning Examples - Makefile Help"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Main targets:"
	@echo "  all           - Build all examples (default)"
	@echo "  examples      - Build all examples"
	@echo "  tests         - Build all tests"
	@echo "  solutions     - Build solution implementations"
	@echo "  clean         - Remove build artifacts"
	@echo "  distclean     - Remove all build artifacts including solutions"
	@echo ""
	@echo "Individual examples:"
	@echo "  vector_add    - Build example 1 (vector addition)"
	@echo "  matrix_add    - Build example 2 (matrix addition)"
	@echo "  matrix_mul    - Build example 3 (matrix multiplication)"
	@echo "  reduction     - Build example 4 (reduction operations)"
	@echo "  conv          - Build example 5 (convolution)"
	@echo "  nn_forward    - Build example 6 (NN forward pass)"
	@echo "  nn_backward   - Build example 7 (NN backward pass)"
	@echo "  neural_net    - Build example 8 (complete neural network)"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run all tests"
	@echo "  test-vector   - Run vector addition tests"
	@echo "  test-matrix   - Run matrix operation tests"
	@echo "  test-nn       - Run neural network tests"
	@echo ""
	@echo "Running examples:"
	@echo "  run-01        - Run vector addition example"
	@echo "  run-02        - Run matrix addition example"
	@echo "  run-03        - Run matrix multiplication example"
	@echo "  run-04        - Run reduction example"
	@echo "  run-05        - Run convolution example"
	@echo "  run-06        - Run NN forward pass example"
	@echo "  run-07        - Run NN backward pass example"
	@echo "  run-08        - Run complete NN training"
	@echo ""
	@echo "Benchmarking and profiling:"
	@echo "  benchmark     - Run performance benchmarks"
	@echo "  profile-<ex>  - Profile specific example (e.g., profile-vector_add)"
	@echo ""
	@echo "Configuration:"
	@echo "  check-cuda    - Verify CUDA installation"
	@echo "  debug         - Build with debug information"
	@echo "  ARCH=sm_XX    - Set compute capability (default: sm_60)"
	@echo ""
	@echo "Examples:"
	@echo "  make vector_add"
	@echo "  make run-01"
	@echo "  make test-vector"
	@echo "  make ARCH=sm_75 all"
	@echo "  make profile-matrix_mul"
