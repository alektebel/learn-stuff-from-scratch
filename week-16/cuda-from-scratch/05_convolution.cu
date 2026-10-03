/*
 * Example 5: 2D Convolution in CUDA
 * 
 * Implements 2D image convolution for filtering operations
 * 
 * Learning Goals:
 * - Constant memory for filter kernel
 * - Handling boundary conditions
 * - Stencil computations
 * - Shared memory tiling with halos
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

#define MAX_FILTER_SIZE 11

// TODO: Store filter in constant memory for fast access
// __constant__ float c_filter[MAX_FILTER_SIZE * MAX_FILTER_SIZE];

/*
 * TODO: Implement 2D convolution kernel
 * 
 * IMPLEMENTATION GUIDELINES:
 * 1. Each thread computes one output pixel
 * 2. Apply filter to neighborhood of input
 * 3. Handle boundaries (clamp, wrap, or zero-pad)
 * 4. Use constant memory for filter
 */
__global__ void convolve2D(const float* input, float* output,
                            int width, int height, int filterSize) {
    // TODO: Calculate output position
    // TODO: Apply filter to input neighborhood
    // TODO: Handle boundary conditions
    // TODO: Write result
}

int main(int argc, char** argv) {
    printf("2D Convolution Example\n");
    printf("TODO: Implement convolution with various filters\n");
    printf("- Gaussian blur\n");
    printf("- Edge detection (Sobel)\n");
    printf("- Sharpening\n");
    return 0;
}

/*
 * IMPLEMENTATION STEPS:
 * 1. Load filter into constant memory
 * 2. Implement basic convolution kernel
 * 3. Add boundary handling
 * 4. Optimize with shared memory tiling
 * 5. Test with different filter sizes
 */
