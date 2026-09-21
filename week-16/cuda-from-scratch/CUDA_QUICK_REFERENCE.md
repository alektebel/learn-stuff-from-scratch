# CUDA Quick Reference

A cheat sheet for CUDA programming concepts and syntax.

## Basic Program Structure

```cpp
#include <cuda_runtime.h>

// Kernel definition (runs on GPU)
__global__ void myKernel(float* data, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        data[idx] = data[idx] * 2.0f;
    }
}

int main() {
    // 1. Allocate host memory
    float* h_data = (float*)malloc(N * sizeof(float));
    
    // 2. Initialize data
    // ...
    
    // 3. Allocate device memory
    float* d_data;
    cudaMalloc(&d_data, N * sizeof(float));
    
    // 4. Copy data to device
    cudaMemcpy(d_data, h_data, N * sizeof(float), cudaMemcpyHostToDevice);
    
    // 5. Launch kernel
    int threadsPerBlock = 256;
    int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;
    myKernel<<<blocksPerGrid, threadsPerBlock>>>(d_data, N);
    
    // 6. Copy results back
    cudaMemcpy(h_data, d_data, N * sizeof(float), cudaMemcpyDeviceToHost);
    
    // 7. Cleanup
    cudaFree(d_data);
    free(h_data);
    
    return 0;
}
```

## Thread Indexing

### 1D Indexing
```cpp
int idx = blockIdx.x * blockDim.x + threadIdx.x;
```

### 2D Indexing
```cpp
int row = blockIdx.y * blockDim.y + threadIdx.y;
int col = blockIdx.x * blockDim.x + threadIdx.x;
int idx = row * width + col;  // Row-major
```

### 3D Indexing
```cpp
int x = blockIdx.x * blockDim.x + threadIdx.x;
int y = blockIdx.y * blockDim.y + threadIdx.y;
int z = blockIdx.z * blockDim.z + threadIdx.z;
int idx = z * (width * height) + y * width + x;
```

## Built-in Variables

```cpp
// Thread indices within block
threadIdx.x, threadIdx.y, threadIdx.z  // 0 to blockDim-1

// Block indices within grid
blockIdx.x, blockIdx.y, blockIdx.z     // 0 to gridDim-1

// Block dimensions
blockDim.x, blockDim.y, blockDim.z     // Threads per block

// Grid dimensions
gridDim.x, gridDim.y, gridDim.z        // Blocks per grid
```

## Function Qualifiers

```cpp
__global__ void kernel()    // Runs on GPU, called from CPU
__device__ void helper()    // Runs on GPU, called from GPU
__host__ void cpuFunc()     // Runs on CPU (default)
__host__ __device__ both()  // Can run on both
```

## Memory Management

### Allocation
```cpp
cudaMalloc(&d_ptr, size);              // Allocate on device
cudaMallocHost(&h_ptr, size);          // Pinned host memory
cudaMallocManaged(&ptr, size);         // Unified memory
```

### Copy
```cpp
cudaMemcpy(dst, src, size, cudaMemcpyHostToDevice);
cudaMemcpy(dst, src, size, cudaMemcpyDeviceToHost);
cudaMemcpy(dst, src, size, cudaMemcpyDeviceToDevice);
cudaMemcpy(dst, src, size, cudaMemcpyHostToHost);
```

### Free
```cpp
cudaFree(d_ptr);                       // Free device memory
cudaFreeHost(h_ptr);                   // Free pinned memory
```

### Memory Set
```cpp
cudaMemset(d_ptr, value, size);        // Set device memory
```

## Kernel Launch Configuration

### 1D Grid
```cpp
int threads = 256;
int blocks = (N + threads - 1) / threads;
kernel<<<blocks, threads>>>(args);
```

### 2D Grid
```cpp
dim3 threads(16, 16);
dim3 blocks((width + 16 - 1) / 16, (height + 16 - 1) / 16);
kernel<<<blocks, threads>>>(args);
```

### With Shared Memory
```cpp
int sharedMemSize = 256 * sizeof(float);
kernel<<<blocks, threads, sharedMemSize>>>(args);
```

## Shared Memory

### Static Allocation
```cpp
__global__ void kernel() {
    __shared__ float cache[256];
    // Use cache...
}
```

### Dynamic Allocation
```cpp
__global__ void kernel() {
    extern __shared__ float cache[];  // Size specified at launch
    // Use cache...
}

// Launch
kernel<<<blocks, threads, sharedMemSize>>>(args);
```

## Synchronization

```cpp
__syncthreads();              // Block-level barrier
__syncwarp();                 // Warp-level barrier (CUDA 9+)

cudaDeviceSynchronize();      // Wait for all kernels to finish
cudaStreamSynchronize(stream); // Wait for stream to finish
```

## Atomic Operations

```cpp
atomicAdd(&addr, value);      // Atomic addition
atomicSub(&addr, value);      // Atomic subtraction
atomicMin(&addr, value);      // Atomic minimum
atomicMax(&addr, value);      // Atomic maximum
atomicCAS(&addr, cmp, val);   // Compare-and-swap
atomicExch(&addr, value);     // Atomic exchange
```

## Warp Operations (CUDA 9+)

```cpp
// Warp shuffle (exchange values between threads)
__shfl_sync(mask, var, srcLane);
__shfl_up_sync(mask, var, delta);
__shfl_down_sync(mask, var, delta);
__shfl_xor_sync(mask, var, laneMask);

// Warp voting
__all_sync(mask, predicate);   // All threads true?
__any_sync(mask, predicate);   // Any thread true?
__ballot_sync(mask, predicate); // Bitmask of true threads
```

## Error Checking

```cpp
#define CUDA_CHECK(call) \
do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error: %s (err_num=%d) at %s:%d\n", \
                cudaGetErrorString(err), err, __FILE__, __LINE__); \
        exit(EXIT_FAILURE); \
    } \
} while(0)

// Usage
CUDA_CHECK(cudaMalloc(&d_ptr, size));
CUDA_CHECK(cudaMemcpy(dst, src, size, cudaMemcpyHostToDevice));

// Check kernel launch
kernel<<<blocks, threads>>>(args);
CUDA_CHECK(cudaGetLastError());
CUDA_CHECK(cudaDeviceSynchronize());
```

## Timing

```cpp
// Using CUDA events
cudaEvent_t start, stop;
cudaEventCreate(&start);
cudaEventCreate(&stop);

cudaEventRecord(start);
// ... GPU work ...
cudaEventRecord(stop);

cudaEventSynchronize(stop);
float milliseconds = 0;
cudaEventElapsedTime(&milliseconds, start, stop);

cudaEventDestroy(start);
cudaEventDestroy(stop);
```

## Common Patterns

### Reduction
```cpp
__global__ void reduce(float* input, float* output, int N) {
    __shared__ float sdata[256];
    
    int tid = threadIdx.x;
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    
    sdata[tid] = (idx < N) ? input[idx] : 0.0f;
    __syncthreads();
    
    for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
        if (tid < stride) {
            sdata[tid] += sdata[tid + stride];
        }
        __syncthreads();
    }
    
    if (tid == 0) {
        output[blockIdx.x] = sdata[0];
    }
}
```

### Tiled Matrix Multiply
```cpp
#define TILE_SIZE 16

__global__ void matmul(float* A, float* B, float* C, int N) {
    __shared__ float tileA[TILE_SIZE][TILE_SIZE];
    __shared__ float tileB[TILE_SIZE][TILE_SIZE];
    
    int row = blockIdx.y * TILE_SIZE + threadIdx.y;
    int col = blockIdx.x * TILE_SIZE + threadIdx.x;
    
    float sum = 0.0f;
    
    for (int t = 0; t < (N + TILE_SIZE - 1) / TILE_SIZE; t++) {
        // Load tiles
        if (row < N && t * TILE_SIZE + threadIdx.x < N)
            tileA[threadIdx.y][threadIdx.x] = A[row * N + t * TILE_SIZE + threadIdx.x];
        else
            tileA[threadIdx.y][threadIdx.x] = 0.0f;
            
        if (col < N && t * TILE_SIZE + threadIdx.y < N)
            tileB[threadIdx.y][threadIdx.x] = B[(t * TILE_SIZE + threadIdx.y) * N + col];
        else
            tileB[threadIdx.y][threadIdx.x] = 0.0f;
            
        __syncthreads();
        
        // Compute
        for (int k = 0; k < TILE_SIZE; k++) {
            sum += tileA[threadIdx.y][k] * tileB[k][threadIdx.x];
        }
        
        __syncthreads();
    }
    
    if (row < N && col < N) {
        C[row * N + col] = sum;
    }
}
```

## Device Properties

```cpp
cudaDeviceProp prop;
cudaGetDeviceProperties(&prop, 0);

printf("Device: %s\n", prop.name);
printf("Compute capability: %d.%d\n", prop.major, prop.minor);
printf("Max threads per block: %d\n", prop.maxThreadsPerBlock);
printf("Max block dimensions: %d x %d x %d\n",
       prop.maxThreadsDim[0], prop.maxThreadsDim[1], prop.maxThreadsDim[2]);
printf("Max grid dimensions: %d x %d x %d\n",
       prop.maxGridSize[0], prop.maxGridSize[1], prop.maxGridSize[2]);
printf("Shared memory per block: %zu bytes\n", prop.sharedMemPerBlock);
printf("Total global memory: %zu bytes\n", prop.totalGlobalMem);
printf("Warp size: %d\n", prop.warpSize);
```

## Common Block Sizes

| Dimension | Typical Sizes | Use Case |
|-----------|---------------|----------|
| 1D        | 128, 256, 512, 1024 | Vectors, simple arrays |
| 2D        | (16,16), (32,32), (16,32) | Matrices, images |
| 3D        | (8,8,8), (16,8,4) | Volumes, 3D grids |

## Optimization Guidelines

### Memory
- ✅ Coalesce global memory accesses
- ✅ Use shared memory for data reuse
- ✅ Minimize divergent branches
- ✅ Align data structures

### Execution
- ✅ Maximize occupancy (balance threads, registers, shared memory)
- ✅ Minimize warp divergence
- ✅ Avoid bank conflicts in shared memory
- ✅ Use async operations when possible

### Algorithm
- ✅ Prefer more computation over memory access
- ✅ Use tiling for large datasets
- ✅ Consider using libraries (cuBLAS, cuDNN)

## Compile Flags

```bash
nvcc -arch=sm_75 program.cu          # Specify compute capability
nvcc -O3 program.cu                  # Optimization level
nvcc -g -G program.cu                # Debug mode
nvcc -lineinfo program.cu            # Line info for profiling
nvcc -use_fast_math program.cu       # Fast math operations
nvcc -Xptxas -v program.cu           # Show register usage
```

## Profiling Commands

```bash
# Legacy profiler
nvprof ./program

# Modern kernel profiler
ncu --set full ./program

# System timeline
nsys profile ./program

# Memory checker
cuda-memcheck ./program
```

## Common Pitfalls

1. **Forgetting bounds check**: Always `if (idx < N)`
2. **Wrong grid size**: Use `(N + threads - 1) / threads`
3. **Missing __syncthreads()**: Required when threads share data
4. **Shared memory races**: Sync before and after shared memory use
5. **Not checking errors**: Use CUDA_CHECK macro
6. **Memory leaks**: Always free allocated memory

## Quick Tips

- Start with small problem sizes for debugging
- Always verify results against CPU implementation
- Profile before optimizing
- Use existing libraries when possible
- Read the CUDA Programming Guide for details

## Resources

- [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [cuBLAS Documentation](https://docs.nvidia.com/cuda/cublas/)
- [cuDNN Documentation](https://docs.nvidia.com/deeplearning/cudnn/)
