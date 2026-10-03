# Getting Started with CUDA Programming

This quick guide will help you start learning CUDA programming immediately.

## Prerequisites Check

### 1. Verify CUDA Installation

```bash
# Check CUDA compiler
nvcc --version

# Expected output: CUDA compilation tools, release 11.x or higher
```

```bash
# Check GPU availability
nvidia-smi

# Expected output: GPU information and driver version
```

If either command fails, you need to install CUDA Toolkit first:
- [CUDA Toolkit Download](https://developer.nvidia.com/cuda-downloads)

### 2. Verify Your GPU

```bash
# Get GPU compute capability
nvidia-smi --query-gpu=compute_cap --format=csv
```

Update the Makefile `ARCH` variable to match your GPU:
- RTX 30 series: `sm_86`
- RTX 20 series: `sm_75`
- GTX 10 series: `sm_61`
- Older GPUs: Check [NVIDIA's compute capability table](https://developer.nvidia.com/cuda-gpus)

## Quick Start (5 minutes)

### Step 1: Build First Example

```bash
# Navigate to CUDA directory
cd cuda-from-scratch

# Build vector addition example
make vector_add

# Run it
./01_vector_addition 1000000
```

**Expected output:**
```
Vector Addition: N = 1000000 elements
Initializing input vectors...
Performing vector addition on GPU...
Kernel execution time: ~0.5-2 ms
Verifying results...
✓ Verification PASSED
```

### Step 2: Examine the Code

Open `01_vector_addition.cu` and look for `TODO` comments. These guide you through:
1. Writing your first CUDA kernel
2. Managing GPU memory
3. Launching kernels
4. Verifying results

### Step 3: Try Implementing It Yourself

```bash
# Make a backup
cp 01_vector_addition.cu 01_vector_addition.cu.backup

# Edit the file and implement the TODOs
nano 01_vector_addition.cu  # or use your favorite editor

# Build and test
make vector_add
./01_vector_addition 1000000
```

## Learning Path

### Week 1: Fundamentals (3-5 hours)

**Day 1-2: Vector Addition (Example 1)**
- Goal: Understand basic CUDA structure
- Time: 1-2 hours
- [Read: README.md - Example 1 section](README.md#example-1-vector-addition)
- [Guide: IMPLEMENTATION_GUIDE.md - Example 1](IMPLEMENTATION_GUIDE.md#example-1-vector-addition)

**Day 3-4: Matrix Addition (Example 2)**
- Goal: Work with 2D data
- Time: 1-2 hours
- [Read: README.md - Example 2 section](README.md#example-2-matrix-addition)

**Day 5: Review and Practice**
- Run tests: `make test-vector test-matrix`
- Experiment with different sizes
- Profile with `nvprof`

### Week 2: Optimization (4-6 hours)

**Day 1-3: Matrix Multiplication (Example 3)**
- Goal: Master shared memory optimization
- Time: 2-3 hours
- Key concept: 5-10x speedup with tiling
- [Guide: IMPLEMENTATION_GUIDE.md - Example 3](IMPLEMENTATION_GUIDE.md#example-3-matrix-multiplication)

**Day 4-5: Reduction (Example 4)**
- Goal: Learn parallel patterns
- Time: 2-3 hours
- Key concept: Tree-based reduction

### Week 3: Advanced Patterns (4-6 hours)

**Day 1-3: Convolution (Example 5)**
- Goal: Implement stencil operations
- Time: 2-3 hours
- Applications: Image processing

**Day 4-5: Review and Optimize**
- Compare your implementations with solutions
- Profile and optimize
- Understand bottlenecks

### Week 4-5: Neural Networks (8-12 hours)

**Days 1-3: Forward Pass (Example 6)**
- Goal: Implement NN layers
- Time: 3-4 hours

**Days 4-6: Backward Pass (Example 7)**
- Goal: Implement backpropagation
- Time: 3-4 hours

**Days 7-10: Complete Network (Example 8)**
- Goal: Train on MNIST
- Time: 4-6 hours
- Target: >95% accuracy

## Daily Practice Routine

### 15-Minute Quick Session
```bash
# Run and time an example
./01_vector_addition 10000000

# Try different block sizes in the code
# Compare performance
```

### 1-Hour Deep Dive
1. Read implementation guide for one example (15 min)
2. Implement one TODO section (30 min)
3. Test and verify (10 min)
4. Review solution if stuck (5 min)

### 2-Hour Project Session
1. Complete one full example (60 min)
2. Run tests and benchmarks (15 min)
3. Profile with nvprof (15 min)
4. Compare with solution (15 min)
5. Document learnings (15 min)

## Common First-Time Issues

### Issue 1: "nvcc: command not found"

**Solution:** Add CUDA to PATH
```bash
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

### Issue 2: "no CUDA-capable device detected"

**Possible causes:**
1. No NVIDIA GPU in system
2. GPU drivers not installed
3. GPU not enabled in BIOS

**Check:**
```bash
lspci | grep -i nvidia  # Should show your GPU
```

### Issue 3: Compilation errors about compute capability

**Solution:** Update Makefile
```bash
# In Makefile, change:
ARCH = sm_XX  # to your GPU's compute capability
```

### Issue 4: Segmentation fault

**Common causes:**
1. Forgot to check `if (idx < N)` in kernel
2. Incorrect memory size in malloc/cudaMalloc
3. Not synchronizing before copying results

**Debug with:**
```bash
cuda-memcheck ./program
```

## Tips for Success

### 1. Start Small
- Begin with tiny arrays (N=10) to verify correctness
- Scale up once working correctly
- Easier to debug small sizes

### 2. Print Debug Info
```cpp
// In kernel
if (threadIdx.x == 0 && blockIdx.x == 0) {
    printf("Debug: value = %f\n", someVariable);
}
```

### 3. Verify Incrementally
- Test each function separately
- Don't wait until everything is complete
- Fix bugs immediately when found

### 4. Use the Tools
```bash
# Memory errors
cuda-memcheck ./program

# Performance profiling
nvprof ./program

# Detailed kernel analysis
ncu --set full ./program
```

### 5. Compare with CPU
Always implement a CPU version first to verify correctness:
```cpp
void cpuVersion(...) {
    for (int i = 0; i < N; i++) {
        // Simple sequential version
    }
}
```

## Resources

### Documentation
- [CUDA C Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/) - Official guide
- [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/) - Optimization tips

### Tools
- **nvprof** - Legacy profiler (simple, good for learning)
- **Nsight Compute** - Modern kernel profiler (detailed)
- **Nsight Systems** - Timeline profiler (system-wide view)
- **cuda-gdb** - GPU debugger

### Community
- [NVIDIA Developer Forums](https://forums.developer.nvidia.com/c/accelerated-computing/cuda/206)
- [Stack Overflow - CUDA tag](https://stackoverflow.com/questions/tagged/cuda)

## Next Steps

After completing all examples:

1. **Optimize further**
   - Try different block sizes
   - Experiment with different strategies
   - Profile and improve

2. **Integrate with libraries**
   - Use cuBLAS for matrix operations
   - Use cuDNN for deep learning
   - Compare performance

3. **Build something new**
   - Image processing application
   - Scientific simulation
   - Custom ML model

4. **Contribute**
   - Share your optimizations
   - Add new examples
   - Help others learn

## Getting Help

If you're stuck:

1. **Check the implementation guide**
   - Detailed instructions for each example
   - Code snippets and explanations

2. **Review the solution**
   - See how it's supposed to work
   - Understand the approach
   - Compare with your implementation

3. **Run the tests**
   ```bash
   make test
   ```

4. **Profile to find issues**
   ```bash
   nvprof ./your_program
   ```

Happy CUDA programming! 🚀

Remember: **Learn by doing.** Don't just read - implement, experiment, and break things!
