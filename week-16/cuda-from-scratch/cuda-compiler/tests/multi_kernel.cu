/*
 * Test input: Multiple Kernels in One File
 *
 * Tests that the compiler handles multiple __global__ kernels.
 *
 * To compile with our tiny compiler:
 *   ../cuda_compiler multi_kernel.cu -o multi_kernel.ptx
 */

#include <cuda_runtime.h>

/* Kernel 1: scale a vector by a scalar */
__global__ void scaleVector(float* A, float scalar, int N)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        A[idx] = A[idx] * scalar;
    }
}

/* Kernel 2: element-wise multiply */
__global__ void vectorMul(float* A, float* B, float* C, int N)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        C[idx] = A[idx] * B[idx];
    }
}
