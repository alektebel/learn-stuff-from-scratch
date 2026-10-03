/*
 * Test Suite for Neural Network Components
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

__global__ void reluKernel(float* data, int size) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        data[idx] = fmaxf(0.0f, data[idx]);
    }
}

bool testReLU() {
    int N = 100;
    float *h_data = (float*)malloc(N * sizeof(float));
    float *d_data;
    
    for (int i = 0; i < N; i++) {
        h_data[i] = (float)i - 50.0f;  // Values from -50 to 49
    }
    
    CUDA_CHECK(cudaMalloc(&d_data, N * sizeof(float)));
    CUDA_CHECK(cudaMemcpy(d_data, h_data, N * sizeof(float), cudaMemcpyHostToDevice));
    
    int threadsPerBlock = 256;
    int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;
    reluKernel<<<blocksPerGrid, threadsPerBlock>>>(d_data, N);
    
    CUDA_CHECK(cudaMemcpy(h_data, d_data, N * sizeof(float), cudaMemcpyDeviceToHost));
    
    bool passed = true;
    for (int i = 0; i < N; i++) {
        float input = (float)i - 50.0f;
        float expected = (input > 0.0f) ? input : 0.0f;
        if (fabs(h_data[i] - expected) > 1e-5) {
            passed = false;
            break;
        }
    }
    
    free(h_data);
    CUDA_CHECK(cudaFree(d_data));
    
    return passed;
}

int main() {
    printf("Neural Network Components Test Suite\n");
    printf("====================================\n\n");
    
    printf("Test 1: ReLU activation ... ");
    if (testReLU()) {
        printf("PASSED\n");
    } else {
        printf("FAILED\n");
    }
    
    printf("\nMore tests to be implemented:\n");
    printf("- Fully connected layer forward\n");
    printf("- Softmax activation\n");
    printf("- Loss functions\n");
    printf("- Backpropagation\n");
    printf("- Weight updates\n");
    
    return 0;
}
