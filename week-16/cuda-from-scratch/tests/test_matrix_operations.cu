/*
 * Test Suite for Matrix Operations
 */

#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>
#include <math.h>

#define CUDA_CHECK(call) \
do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error: %s at %s:%d\n", \
                cudaGetErrorString(err), __FILE__, __LINE__); \
        exit(EXIT_FAILURE); \
    } \
} while(0)

#define TILE_SIZE 16

__global__ void matrixAddKernel(const float* A, const float* B, float* C,
                                 int rows, int cols) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (row < rows && col < cols) {
        int idx = row * cols + col;
        C[idx] = A[idx] + B[idx];
    }
}

bool testMatrixAddition(int rows, int cols) {
    size_t bytes = rows * cols * sizeof(float);
    float *h_A, *h_B, *h_C;
    float *d_A, *d_B, *d_C;
    
    h_A = (float*)malloc(bytes);
    h_B = (float*)malloc(bytes);
    h_C = (float*)malloc(bytes);
    
    for (int i = 0; i < rows * cols; i++) {
        h_A[i] = (float)i * 0.1f;
        h_B[i] = (float)i * 0.2f;
    }
    
    CUDA_CHECK(cudaMalloc(&d_A, bytes));
    CUDA_CHECK(cudaMalloc(&d_B, bytes));
    CUDA_CHECK(cudaMalloc(&d_C, bytes));
    
    CUDA_CHECK(cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, h_B, bytes, cudaMemcpyHostToDevice));
    
    dim3 threadsPerBlock(16, 16);
    dim3 blocksPerGrid(
        (cols + threadsPerBlock.x - 1) / threadsPerBlock.x,
        (rows + threadsPerBlock.y - 1) / threadsPerBlock.y
    );
    
    matrixAddKernel<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, rows, cols);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    
    CUDA_CHECK(cudaMemcpy(h_C, d_C, bytes, cudaMemcpyDeviceToHost));
    
    bool passed = true;
    for (int i = 0; i < rows * cols; i++) {
        float expected = h_A[i] + h_B[i];
        if (fabs(h_C[i] - expected) > 1e-5) {
            passed = false;
            break;
        }
    }
    
    free(h_A);
    free(h_B);
    free(h_C);
    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));
    
    return passed;
}

int main() {
    printf("Matrix Operations Test Suite\n");
    printf("=============================\n\n");
    
    printf("Matrix Addition Tests:\n");
    
    struct {
        int rows, cols;
    } tests[] = {
        {10, 10},
        {100, 100},
        {128, 256},
        {1024, 1024}
    };
    
    int numTests = sizeof(tests) / sizeof(tests[0]);
    int passed = 0;
    
    for (int i = 0; i < numTests; i++) {
        printf("Test %d: %dx%d ... ", i+1, tests[i].rows, tests[i].cols);
        if (testMatrixAddition(tests[i].rows, tests[i].cols)) {
            printf("PASSED\n");
            passed++;
        } else {
            printf("FAILED\n");
        }
    }
    
    printf("\n%d/%d tests passed\n", passed, numTests);
    return (passed == numTests) ? 0 : 1;
}
