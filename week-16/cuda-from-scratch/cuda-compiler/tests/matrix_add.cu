/*
 * Test input: Matrix Addition Kernel
 *
 * Each thread computes one element of C = A + B for 2-D matrices.
 * Demonstrates 2D thread indexing.
 *
 * To compile with our tiny compiler:
 *   ../cuda_compiler matrix_add.cu -o matrix_add.ptx
 */

#include <cuda_runtime.h>

__global__ void matrixAdd(float* A, float* B, float* C, int rows, int cols)
{
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    int idx = row * cols + col;
    if (row < rows) {
        if (col < cols) {
            C[idx] = A[idx] + B[idx];
        }
    }
}
