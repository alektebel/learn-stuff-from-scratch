/*
 * Example 3: Matrix Multiplication in CUDA
 * 
 * This example demonstrates optimization with shared memory:
 * - Tiled matrix multiplication
 * - Shared memory usage
 * - Thread synchronization (__syncthreads)
 * - Performance comparison (naive vs optimized)
 * 
 * Learning Goals:
 * - Understand shared memory benefits
 * - Implement tiling for data reuse
 * - Master __syncthreads() usage
 * - Analyze memory access patterns
 * 
 * Matrix multiplication: C = A * B
 * where A is MxK, B is KxN, and C is MxN
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

#define TILE_SIZE 16

/*
 * TODO: Implement naive matrix multiplication kernel
 * 
 * IMPLEMENTATION GUIDELINES:
 * 
 * For C = A * B:
 * - A is MxK (M rows, K columns)
 * - B is KxN (K rows, N columns)  
 * - C is MxN (M rows, N columns)
 * 
 * Each thread computes one element C[row][col]:
 * C[row][col] = sum(A[row][k] * B[k][col]) for k = 0 to K-1
 * 
 * Steps:
 * 1. Calculate output position (row, col)
 * 2. Check bounds
 * 3. Compute dot product by iterating over K dimension
 * 4. Write result to C
 * 
 * Note: This version uses only global memory (slow but simple)
 */
__global__ void matrixMulNaive(const float* A, const float* B, float* C,
                                int M, int N, int K) {
    // TODO: Calculate output row and column
    // int row = blockIdx.y * blockDim.y + threadIdx.y;
    // int col = blockIdx.x * blockDim.x + threadIdx.x;
    
    // TODO: Check bounds
    // if (row < M && col < N) {
    //     TODO: Compute dot product
    //     float sum = 0.0f;
    //     for (int k = 0; k < K; k++) {
    //         // A is row-major: A[row][k] = A[row * K + k]
    //         // B is row-major: B[k][col] = B[k * N + col]
    //         sum += A[row * K + k] * B[k * N + col];
    //     }
    //     
    //     TODO: Write result
    //     C[row * N + col] = sum;
    // }
}

/*
 * TODO: Implement tiled matrix multiplication with shared memory
 * 
 * IMPLEMENTATION GUIDELINES:
 * 
 * This optimized version uses shared memory to reduce global memory accesses:
 * 
 * 1. Each block loads tiles of A and B into shared memory
 * 2. All threads in the block can reuse this data
 * 3. Synchronize between loading and computing
 * 4. Process tiles one at a time, accumulating results
 * 
 * Memory access reduction:
 * - Naive: Each element loaded K times from global memory
 * - Tiled: Each element loaded once per tile from global memory
 * - Expected speedup: 5-10x for typical problem sizes
 * 
 * Key concepts:
 * - __shared__ memory: On-chip, shared by threads in a block
 * - __syncthreads(): Barrier synchronization
 * - Tiling: Breaking computation into smaller chunks
 */
__global__ void matrixMulTiled(const float* A, const float* B, float* C,
                                int M, int N, int K) {
    // TODO: Step 1 - Allocate shared memory for tiles
    // __shared__ float tileA[TILE_SIZE][TILE_SIZE];
    // __shared__ float tileB[TILE_SIZE][TILE_SIZE];
    
    // TODO: Step 2 - Calculate indices
    // int row = blockIdx.y * TILE_SIZE + threadIdx.y;
    // int col = blockIdx.x * TILE_SIZE + threadIdx.x;
    // int tx = threadIdx.x;
    // int ty = threadIdx.y;
    
    // TODO: Step 3 - Initialize accumulator
    // float sum = 0.0f;
    
    // TODO: Step 4 - Loop over tiles
    // int numTiles = (K + TILE_SIZE - 1) / TILE_SIZE;
    // for (int t = 0; t < numTiles; t++) {
    //     
    //     TODO: Step 4a - Load tile from A into shared memory
    //     int aCol = t * TILE_SIZE + tx;
    //     if (row < M && aCol < K) {
    //         tileA[ty][tx] = A[row * K + aCol];
    //     } else {
    //         tileA[ty][tx] = 0.0f;  // Padding for out-of-bounds
    //     }
    //     
    //     TODO: Step 4b - Load tile from B into shared memory
    //     int bRow = t * TILE_SIZE + ty;
    //     if (bRow < K && col < N) {
    //         tileB[ty][tx] = B[bRow * N + col];
    //     } else {
    //         tileB[ty][tx] = 0.0f;  // Padding
    //     }
    //     
    //     TODO: Step 4c - Synchronize to ensure tiles are loaded
    //     __syncthreads();
    //     
    //     TODO: Step 4d - Compute partial dot product using shared memory
    //     for (int k = 0; k < TILE_SIZE; k++) {
    //         sum += tileA[ty][k] * tileB[k][tx];
    //     }
    //     
    //     TODO: Step 4e - Synchronize before loading next tile
    //     __syncthreads();
    // }
    
    // TODO: Step 5 - Write result
    // if (row < M && col < N) {
    //     C[row * N + col] = sum;
    // }
}

void matrixMul(const float* h_A, const float* h_B, float* h_C,
               int M, int N, int K, bool useTiled) {
    size_t bytesA = M * K * sizeof(float);
    size_t bytesB = K * N * sizeof(float);
    size_t bytesC = M * N * sizeof(float);
    
    // Allocate device memory
    float *d_A, *d_B, *d_C;
    CUDA_CHECK(cudaMalloc(&d_A, bytesA));
    CUDA_CHECK(cudaMalloc(&d_B, bytesB));
    CUDA_CHECK(cudaMalloc(&d_C, bytesC));
    
    // Copy inputs to device
    CUDA_CHECK(cudaMemcpy(d_A, h_A, bytesA, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, h_B, bytesB, cudaMemcpyHostToDevice));
    
    // Configure grid and block dimensions
    dim3 threadsPerBlock(TILE_SIZE, TILE_SIZE);
    dim3 blocksPerGrid(
        (N + TILE_SIZE - 1) / TILE_SIZE,
        (M + TILE_SIZE - 1) / TILE_SIZE
    );
    
    // Launch appropriate kernel
    if (useTiled) {
        matrixMulTiled<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, M, N, K);
    } else {
        matrixMulNaive<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, M, N, K);
    }
    
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    
    // Copy result back
    CUDA_CHECK(cudaMemcpy(h_C, d_C, bytesC, cudaMemcpyDeviceToHost));
    
    // Free device memory
    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));
}

int main(int argc, char** argv) {
    int M = 1024, N = 1024, K = 1024;
    
    if (argc > 1) M = atoi(argv[1]);
    if (argc > 2) N = atoi(argv[2]);
    if (argc > 3) K = atoi(argv[3]);
    
    printf("Matrix Multiplication: C(%dx%d) = A(%dx%d) * B(%dx%d)\n",
           M, N, M, K, K, N);
    
    // Allocate host memory
    float* h_A = (float*)malloc(M * K * sizeof(float));
    float* h_B = (float*)malloc(K * N * sizeof(float));
    float* h_C_naive = (float*)malloc(M * N * sizeof(float));
    float* h_C_tiled = (float*)malloc(M * N * sizeof(float));
    
    // Initialize matrices
    for (int i = 0; i < M * K; i++) h_A[i] = (float)rand() / RAND_MAX;
    for (int i = 0; i < K * N; i++) h_B[i] = (float)rand() / RAND_MAX;
    
    // Test naive version
    printf("\nTesting naive version...\n");
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    matrixMul(h_A, h_B, h_C_naive, M, N, K, false);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    
    float naiveTime = 0;
    cudaEventElapsedTime(&naiveTime, start, stop);
    printf("Naive kernel time: %.3f ms\n", naiveTime);
    
    // Test tiled version
    printf("\nTesting tiled version...\n");
    cudaEventRecord(start);
    matrixMul(h_A, h_B, h_C_tiled, M, N, K, true);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    
    float tiledTime = 0;
    cudaEventElapsedTime(&tiledTime, start, stop);
    printf("Tiled kernel time: %.3f ms\n", tiledTime);
    printf("Speedup: %.2fx\n", naiveTime / tiledTime);
    
    // Verify results match
    bool match = true;
    for (int i = 0; i < M * N && match; i++) {
        if (fabs(h_C_naive[i] - h_C_tiled[i]) > 1e-3) {
            match = false;
        }
    }
    
    printf("\nResults match: %s\n", match ? "YES" : "NO");
    
    // Cleanup
    free(h_A);
    free(h_B);
    free(h_C_naive);
    free(h_C_tiled);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    
    return 0;
}

/*
 * IMPLEMENTATION CHECKLIST:
 * 
 * Naive Kernel:
 * [ ] Calculate output position (row, col)
 * [ ] Implement dot product loop over K dimension
 * [ ] Handle matrix indexing correctly
 * [ ] Write result to output
 * 
 * Tiled Kernel:
 * [ ] Declare shared memory arrays
 * [ ] Load tiles from global to shared memory
 * [ ] Add __syncthreads() after loading
 * [ ] Compute using shared memory
 * [ ] Add __syncthreads() before next tile
 * [ ] Handle boundary conditions (padding)
 * 
 * EXPECTED OUTPUT:
 * Matrix Multiplication: C(1024x1024) = A(1024x1024) * B(1024x1024)
 * Testing naive version...
 * Naive kernel time: ~50-100 ms
 * Testing tiled version...
 * Tiled kernel time: ~5-15 ms
 * Speedup: 5-10x
 * Results match: YES
 */
