/*
 * Example 7: Neural Network Backward Pass
 * 
 * Implements backpropagation for computing gradients
 * 
 * Learning Goals:
 * - Gradient computation via chain rule
 * - Backpropagation algorithm
 * - Weight updates (SGD)
 * - Numerical gradient checking
 */

#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>

#define CUDA_CHECK(call) \
do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error at %s:%d - %s\n", __FILE__, __LINE__, \
                cudaGetErrorString(err)); \
        exit(EXIT_FAILURE); \
    } \
} while(0)

/*
 * TODO: Implement activation derivatives
 */
__global__ void reluBackward(const float* output, const float* gradOutput,
                              float* gradInput, int size) {
    // TODO: ReLU derivative: 1 if x > 0, else 0
}

/*
 * TODO: Implement FC layer backward pass
 * 
 * Computes three gradients:
 * 1. gradInput = gradOutput @ weights^T
 * 2. gradWeights = input^T @ gradOutput
 * 3. gradBias = sum(gradOutput, axis=0)
 */
__global__ void fullyConnectedBackward(
    const float* input, const float* weights, const float* gradOutput,
    float* gradInput, float* gradWeights, float* gradBias,
    int batchSize, int inputSize, int outputSize) {
    // TODO: Compute gradients
}

/*
 * TODO: Implement SGD weight update
 */
__global__ void sgdUpdate(float* weights, const float* gradients,
                           int size, float learningRate) {
    // TODO: weights -= learningRate * gradients
}

int main() {
    printf("Neural Network Backward Pass\n");
    printf("TODO: Implement backpropagation\n");
    printf("TODO: Verify gradients numerically\n");
    return 0;
}

/*
 * IMPLEMENTATION STEPS:
 * 1. Implement activation derivative kernels
 * 2. Implement FC backward pass
 * 3. Implement gradient descent update
 * 4. Chain backward pass through layers
 * 5. Verify with numerical gradients
 */
