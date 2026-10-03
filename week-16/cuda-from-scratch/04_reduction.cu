/*
 * Example 4: Parallel Reduction in CUDA
 * 
 * Demonstrates parallel reduction pattern for computing sum, min, max, etc.
 * This is a fundamental pattern used in many GPU algorithms.
 * 
 * Learning Goals:
 * - Tree-based parallel reduction
 * - Avoiding warp divergence
 * - Shared memory optimization
 * - Multi-pass reduction for large arrays
 */

#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>
#include <math.h>

#define CUDA_CHECK(call) \
do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error: %s (err_num=%d) at %s:%d\n", \
                cudaGetErrorString(err), err, __FILE__, __LINE__); \
        exit(EXIT_FAILURE); \
    } \
} while(0)

/*
 * TODO: Implement basic parallel reduction (sum)
 * 
 * IMPLEMENTATION GUIDELINES:
 * 
 * Tree-based reduction approach:
 * 1. Each thread loads data into shared memory
 * 2. Threads work together to reduce in a tree pattern
 * 3. Active threads halve each iteration
 * 4. Thread 0 writes final block result
 * 
 * Example for 8 elements:
 * Initial: [1, 2, 3, 4, 5, 6, 7, 8]
 * Step 1:  [3, 7, 11, 15, -, -, -, -]  (stride=1)
 * Step 2:  [10, 26, -, -, -, -, -, -]  (stride=2)
 * Step 3:  [36, -, -, -, -, -, -, -]   (stride=4)
 * Result: 36
 */
__global__ void reduceSumKernel(const float* input, float* output, int N) {
    // TODO: Allocate shared memory (size = blockDim.x)
    extern __shared__ float sdata[];
    
    // TODO: Load data into shared memory
    // int tid = threadIdx.x;
    // int idx = blockIdx.x * blockDim.x + threadIdx.x;
    // sdata[tid] = (idx < N) ? input[idx] : 0.0f;
    // __syncthreads();
    
    // TODO: Perform tree-based reduction
    // for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    //     if (tid < stride) {
    //         sdata[tid] += sdata[tid + stride];
    //     }
    //     __syncthreads();
    // }
    
    // TODO: Thread 0 writes block result
    // if (tid == 0) {
    //     output[blockIdx.x] = sdata[0];
    // }
}

/*
 * Host function for multi-pass reduction
 */
float reduceSum(const float* h_input, int N) {
    const int threadsPerBlock = 256;
    const int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;
    
    // Allocate device memory
    float *d_input, *d_temp;
    CUDA_CHECK(cudaMalloc(&d_input, N * sizeof(float)));
    CUDA_CHECK(cudaMalloc(&d_temp, blocksPerGrid * sizeof(float)));
    
    // Copy input to device
    CUDA_CHECK(cudaMemcpy(d_input, h_input, N * sizeof(float), cudaMemcpyHostToDevice));
    
    // First pass: reduce blocks
    size_t sharedMemSize = threadsPerBlock * sizeof(float);
    reduceSumKernel<<<blocksPerGrid, threadsPerBlock, sharedMemSize>>>(
        d_input, d_temp, N);
    CUDA_CHECK(cudaGetLastError());
    
    // Second pass: reduce block results (if needed)
    float result = 0.0f;
    if (blocksPerGrid == 1) {
        CUDA_CHECK(cudaMemcpy(&result, d_temp, sizeof(float), cudaMemcpyDeviceToHost));
    } else {
        reduceSumKernel<<<1, threadsPerBlock, sharedMemSize>>>(
            d_temp, d_temp, blocksPerGrid);
        CUDA_CHECK(cudaMemcpy(&result, d_temp, sizeof(float), cudaMemcpyDeviceToHost));
    }
    
    CUDA_CHECK(cudaFree(d_input));
    CUDA_CHECK(cudaFree(d_temp));
    
    return result;
}

int main(int argc, char** argv) {
    int N = 1000000;
    if (argc > 1) N = atoi(argv[1]);
    
    printf("Parallel Reduction: N = %d elements\n", N);
    
    // Allocate and initialize input
    float* h_input = (float*)malloc(N * sizeof(float));
    for (int i = 0; i < N; i++) {
        h_input[i] = 1.0f;  // Simple test: sum should equal N
    }
    
    // Compute on GPU
    float gpuSum = reduceSum(h_input, N);
    
    // Verify
    float cpuSum = 0.0f;
    for (int i = 0; i < N; i++) cpuSum += h_input[i];
    
    printf("GPU sum: %.2f\n", gpuSum);
    printf("CPU sum: %.2f\n", cpuSum);
    printf("Match: %s\n", (fabs(gpuSum - cpuSum) < 1e-2) ? "YES" : "NO");
    
    free(h_input);
    return 0;
}

/*
 * IMPLEMENTATION CHECKLIST:
 * [ ] Load data into shared memory with bounds checking
 * [ ] Implement tree-based reduction loop
 * [ ] Add synchronization between iterations
 * [ ] Handle thread 0 writing result
 * [ ] Implement multi-pass for large arrays
 * 
 * OPTIMIZATION OPPORTUNITIES:
 * - Use sequential addressing to avoid divergence
 * - Unroll last warp (no sync needed)
 * - Use warp shuffle instructions
 * - Process multiple elements per thread
 */
