/*
 * Test input: Vector Addition Kernel
 *
 * Classic "Hello World" of CUDA programming.
 * Each GPU thread adds one pair of elements: C[i] = A[i] + B[i]
 *
 * To compile with the real nvcc:
 *   nvcc -ptx vector_add.cu -o vector_add.ptx
 *
 * To compile with our tiny compiler:
 *   ../cuda_compiler vector_add.cu -o vector_add.ptx
 */

#include <cuda_runtime.h>

__global__ void vectorAdd(float* A, float* B, float* C, int N)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        C[idx] = A[idx] + B[idx];
    }
}
