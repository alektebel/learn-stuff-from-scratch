/*
 * Test Suite for Vector Addition
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

__global__ void vectorAddKernel(const float* A, const float* B, float* C, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        C[idx] = A[idx] + B[idx];
    }
}

bool testVectorAddition(int N) {
    float *h_A, *h_B, *h_C;
    float *d_A, *d_B, *d_C;
    
    size_t bytes = N * sizeof(float);
    
    h_A = (float*)malloc(bytes);
    h_B = (float*)malloc(bytes);
    h_C = (float*)malloc(bytes);
    
    for (int i = 0; i < N; i++) {
        h_A[i] = (float)i;
        h_B[i] = (float)(i * 2);
    }
    
    CUDA_CHECK(cudaMalloc(&d_A, bytes));
    CUDA_CHECK(cudaMalloc(&d_B, bytes));
    CUDA_CHECK(cudaMalloc(&d_C, bytes));
    
    CUDA_CHECK(cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, h_B, bytes, cudaMemcpyHostToDevice));
    
    int threadsPerBlock = 256;
    int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;
    
    vectorAddKernel<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, N);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    
    CUDA_CHECK(cudaMemcpy(h_C, d_C, bytes, cudaMemcpyDeviceToHost));
    
    bool passed = true;
    for (int i = 0; i < N; i++) {
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
    printf("Vector Addition Test Suite\n");
    printf("===========================\n\n");
    
    int testSizes[] = {100, 1000, 10000, 100000, 1000000};
    int numTests = sizeof(testSizes) / sizeof(testSizes[0]);
    int passed = 0;
    
    for (int i = 0; i < numTests; i++) {
        printf("Test %d: N=%d ... ", i+1, testSizes[i]);
        if (testVectorAddition(testSizes[i])) {
            printf("PASSED\n");
            passed++;
        } else {
            printf("FAILED\n");
        }
    }
    
    printf("\n%d/%d tests passed\n", passed, numTests);
    return (passed == numTests) ? 0 : 1;
}
