# CUDA Implementation Guide

This comprehensive guide provides detailed implementation instructions for all CUDA examples, from basic vector operations to a complete neural network from scratch.

## Table of Contents

1. [Setup and Prerequisites](#setup-and-prerequisites)
2. [Example 1: Vector Addition](#example-1-vector-addition)
3. [Example 2: Matrix Addition](#example-2-matrix-addition)
4. [Example 3: Matrix Multiplication](#example-3-matrix-multiplication)
5. [Example 4: Reduction Operations](#example-4-reduction-operations)
6. [Example 5: Convolution](#example-5-convolution)
7. [Example 6: Neural Network Forward Pass](#example-6-neural-network-forward-pass)
8. [Example 7: Neural Network Backward Pass](#example-7-neural-network-backward-pass)
9. [Example 8: Complete Neural Network](#example-8-complete-neural-network)

---

## Setup and Prerequisites

### CUDA Installation Verification

```bash
# Check CUDA toolkit version
nvcc --version

# Check GPU information
nvidia-smi

# Expected output should show your GPU and CUDA version
```

### Error Checking Macro

All examples should use this error checking pattern:

```cpp
#define CUDA_CHECK(call) \
do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error: %s (err_num=%d) at %s:%d\n", \
                cudaGetErrorString(err), err, __FILE__, __LINE__); \
        exit(EXIT_FAILURE); \
    } \
} while(0)
```

---

## Example 1: Vector Addition

### Learning Objectives
- Understand CUDA kernel structure
- Learn thread indexing
- Master memory management (allocation, transfer, deallocation)
- Implement error checking

### Implementation Steps

#### Step 1: Define the Kernel

**TODO**: Implement the vector addition kernel

```cpp
// TODO: Implement this kernel
__global__ void vectorAddKernel(const float* A, const float* B, float* C, int N) {
    // IMPLEMENTATION GUIDELINE:
    // 1. Calculate global thread index
    //    - Use blockIdx.x, blockDim.x, and threadIdx.x
    //    - Formula: int idx = blockIdx.x * blockDim.x + threadIdx.x;
    
    // 2. Check bounds to avoid accessing out-of-range memory
    //    - if (idx < N) { ... }
    
    // 3. Perform addition
    //    - C[idx] = A[idx] + B[idx];
    
    // Hint: Each thread processes one element
}
```

**Expected Implementation**:
```cpp
__global__ void vectorAddKernel(const float* A, const float* B, float* C, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        C[idx] = A[idx] + B[idx];
    }
}
```

#### Step 2: Host Function

**TODO**: Implement memory allocation and kernel launch

```cpp
void vectorAdd(const float* h_A, const float* h_B, float* h_C, int N) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Calculate memory size
    //    size_t bytes = N * sizeof(float);
    
    // 2. Allocate device memory (3 arrays: A, B, C)
    //    TODO: Use cudaMalloc() for d_A, d_B, d_C
    //    Example: CUDA_CHECK(cudaMalloc(&d_A, bytes));
    
    // 3. Copy input data from host to device
    //    TODO: Use cudaMemcpy() with cudaMemcpyHostToDevice
    //    Example: CUDA_CHECK(cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice));
    
    // 4. Configure kernel launch parameters
    //    TODO: Set threads per block (typically 256, 512, or 1024)
    //    int threadsPerBlock = 256;
    //    TODO: Calculate number of blocks needed
    //    int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;
    
    // 5. Launch kernel
    //    TODO: vectorAddKernel<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, N);
    //    TODO: Check for kernel launch errors
    //    CUDA_CHECK(cudaGetLastError());
    
    // 6. Wait for GPU to finish
    //    TODO: CUDA_CHECK(cudaDeviceSynchronize());
    
    // 7. Copy result back to host
    //    TODO: Use cudaMemcpy() with cudaMemcpyDeviceToHost
    
    // 8. Free device memory
    //    TODO: Use cudaFree() for all device pointers
}
```

#### Step 3: Main Function with Testing

```cpp
int main(int argc, char** argv) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Parse vector size from command line
    //    int N = (argc > 1) ? atoi(argv[1]) : 1000000;
    
    // 2. Allocate host memory
    //    float* h_A = (float*)malloc(N * sizeof(float));
    //    // TODO: Allocate h_B and h_C
    
    // 3. Initialize input vectors
    //    for (int i = 0; i < N; i++) {
    //        h_A[i] = rand() / (float)RAND_MAX;
    //        h_B[i] = rand() / (float)RAND_MAX;
    //    }
    
    // 4. Call vectorAdd function
    //    vectorAdd(h_A, h_B, h_C, N);
    
    // 5. Verify results
    //    for (int i = 0; i < N; i++) {
    //        float expected = h_A[i] + h_B[i];
    //        if (fabs(h_C[i] - expected) > 1e-5) {
    //            fprintf(stderr, "Verification failed at index %d\n", i);
    //            exit(EXIT_FAILURE);
    //        }
    //    }
    //    printf("Verification: PASSED\n");
    
    // 6. Free host memory
    
    return 0;
}
```

### Performance Measurement

Add timing to measure GPU performance:

```cpp
// TODO: Add timing
cudaEvent_t start, stop;
cudaEventCreate(&start);
cudaEventCreate(&stop);

cudaEventRecord(start);
vectorAddKernel<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, N);
cudaEventRecord(stop);

cudaEventSynchronize(stop);
float milliseconds = 0;
cudaEventElapsedTime(&milliseconds, start, stop);

printf("Kernel execution time: %.3f ms\n", milliseconds);
```

### Testing

Test with various vector sizes:
```bash
./vector_add 100          # Small
./vector_add 1000000      # 1M elements
./vector_add 10000000     # 10M elements
```

### Common Pitfalls

1. **Forgetting bounds checking**: Always check `if (idx < N)`
2. **Wrong grid size**: Use ceiling division for grid size
3. **Not synchronizing**: Call `cudaDeviceSynchronize()` before copying results
4. **Memory leaks**: Always free allocated memory

---

## Example 2: Matrix Addition

### Learning Objectives
- Work with 2D data structures
- Use 2D thread indexing
- Handle non-square matrices
- Optimize grid configuration

### Implementation Steps

#### Step 1: 2D Kernel

**TODO**: Implement 2D matrix addition kernel

```cpp
__global__ void matrixAddKernel(const float* A, const float* B, float* C, 
                                 int rows, int cols) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Calculate 2D indices
    //    int row = blockIdx.y * blockDim.y + threadIdx.y;
    //    int col = blockIdx.x * blockDim.x + threadIdx.x;
    
    // 2. Check bounds
    //    if (row < rows && col < cols) {
    
    // 3. Convert 2D index to 1D (row-major layout)
    //    int idx = row * cols + col;
    
    // 4. Perform addition
    //    C[idx] = A[idx] + B[idx];
}
```

#### Step 2: 2D Grid Configuration

```cpp
// IMPLEMENTATION GUIDELINE:

// 1. Define block dimensions (typically 16x16 or 32x32)
//    dim3 threadsPerBlock(16, 16);

// 2. Calculate grid dimensions
//    dim3 blocksPerGrid(
//        (cols + threadsPerBlock.x - 1) / threadsPerBlock.x,
//        (rows + threadsPerBlock.y - 1) / threadsPerBlock.y
//    );

// 3. Launch kernel
//    matrixAddKernel<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, rows, cols);
```

### Testing

Test with various matrix sizes:
```cpp
// Square matrices
test(100, 100);
test(1000, 1000);

// Non-square matrices
test(1024, 512);
test(2048, 1024);
```

---

## Example 3: Matrix Multiplication

### Learning Objectives
- Understand shared memory
- Implement tiling optimization
- Use thread synchronization
- Compare naive vs optimized implementations

### Implementation Steps

#### Step 1: Naive Implementation

**TODO**: Implement basic matrix multiplication (C = A * B)

```cpp
__global__ void matrixMulNaive(const float* A, const float* B, float* C,
                                int M, int N, int K) {
    // IMPLEMENTATION GUIDELINE:
    // A is MxK, B is KxN, C is MxN
    
    // 1. Calculate output position
    //    int row = blockIdx.y * blockDim.y + threadIdx.y;
    //    int col = blockIdx.x * blockDim.x + threadIdx.x;
    
    // 2. Check bounds
    //    if (row < M && col < N) {
    
    // 3. Compute dot product
    //    float sum = 0.0f;
    //    for (int k = 0; k < K; k++) {
    //        sum += A[row * K + k] * B[k * N + col];
    //    }
    //    C[row * N + col] = sum;
}
```

#### Step 2: Tiled Implementation with Shared Memory

**TODO**: Implement optimized tiled version

```cpp
#define TILE_SIZE 16

__global__ void matrixMulTiled(const float* A, const float* B, float* C,
                                 int M, int N, int K) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Allocate shared memory for tiles
    //    __shared__ float tileA[TILE_SIZE][TILE_SIZE];
    //    __shared__ float tileB[TILE_SIZE][TILE_SIZE];
    
    // 2. Calculate thread indices
    //    int row = blockIdx.y * TILE_SIZE + threadIdx.y;
    //    int col = blockIdx.x * TILE_SIZE + threadIdx.x;
    //    int tx = threadIdx.x;
    //    int ty = threadIdx.y;
    
    // 3. Initialize accumulator
    //    float sum = 0.0f;
    
    // 4. Loop over tiles
    //    for (int t = 0; t < (K + TILE_SIZE - 1) / TILE_SIZE; t++) {
    //        
    //        // 4a. Load tile from A into shared memory
    //        int aCol = t * TILE_SIZE + tx;
    //        if (row < M && aCol < K)
    //            tileA[ty][tx] = A[row * K + aCol];
    //        else
    //            tileA[ty][tx] = 0.0f;
    //        
    //        // 4b. Load tile from B into shared memory
    //        int bRow = t * TILE_SIZE + ty;
    //        if (bRow < K && col < N)
    //            tileB[ty][tx] = B[bRow * N + col];
    //        else
    //            tileB[ty][tx] = 0.0f;
    //        
    //        // 4c. Synchronize to ensure tiles are loaded
    //        __syncthreads();
    //        
    //        // 4d. Compute partial dot product using shared memory
    //        for (int k = 0; k < TILE_SIZE; k++) {
    //            sum += tileA[ty][k] * tileB[k][tx];
    //        }
    //        
    //        // 4e. Synchronize before loading next tile
    //        __syncthreads();
    //    }
    
    // 5. Write result
    //    if (row < M && col < N) {
    //        C[row * N + col] = sum;
    //    }
}
```

### Performance Comparison

```cpp
// TODO: Benchmark both versions
// Expected speedup: 5-10x with tiled version

// Naive version:
// - High global memory traffic
// - Each element loaded K times

// Tiled version:
// - Reduced global memory traffic
// - Data reuse via shared memory
// - Better memory coalescing
```

---

## Example 4: Reduction Operations

### Learning Objectives
- Master parallel reduction patterns
- Avoid warp divergence
- Prevent shared memory bank conflicts
- Use warp shuffle instructions

### Implementation Steps

#### Step 1: Basic Reduction

**TODO**: Implement parallel sum reduction

```cpp
__global__ void reduceSum(const float* input, float* output, int N) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Allocate shared memory
    //    __shared__ float sdata[256];  // assuming 256 threads per block
    
    // 2. Load data into shared memory
    //    int tid = threadIdx.x;
    //    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    //    sdata[tid] = (idx < N) ? input[idx] : 0.0f;
    //    __syncthreads();
    
    // 3. Perform reduction in shared memory (tree-based)
    //    for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    //        if (tid < stride) {
    //            sdata[tid] += sdata[tid + stride];
    //        }
    //        __syncthreads();
    //    }
    
    // 4. Write block result
    //    if (tid == 0) {
    //        output[blockIdx.x] = sdata[0];
    //    }
}
```

#### Step 2: Optimized Reduction (Avoiding Divergence)

```cpp
__global__ void reduceSumOptimized(const float* input, float* output, int N) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Use sequential addressing to avoid divergence
    //    - Start with stride = 1 and double each iteration
    //    - This keeps active threads contiguous
    
    // 2. Unroll last warp (no synchronization needed)
    //    if (tid < 32) {
    //        // Warp-level operations don't need __syncthreads()
    //        sdata[tid] += sdata[tid + 32];
    //        sdata[tid] += sdata[tid + 16];
    //        sdata[tid] += sdata[tid + 8];
    //        sdata[tid] += sdata[tid + 4];
    //        sdata[tid] += sdata[tid + 2];
    //        sdata[tid] += sdata[tid + 1];
    //    }
}
```

#### Step 3: Multi-Pass Reduction

```cpp
// IMPLEMENTATION GUIDELINE:
// For large arrays, use multiple kernel launches

// 1. First pass: Reduce blocks
//    int threadsPerBlock = 256;
//    int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;
//    reduceSum<<<blocksPerGrid, threadsPerBlock>>>(d_input, d_temp, N);

// 2. Second pass: Reduce block results
//    if (blocksPerGrid > 1) {
//        reduceSum<<<1, threadsPerBlock>>>(d_temp, d_output, blocksPerGrid);
//    }
```

---

## Example 5: Convolution

### Learning Objectives
- Implement 2D convolution
- Use constant memory
- Handle boundary conditions
- Optimize with shared memory tiling

### Implementation Steps

#### Step 1: Define Convolution Kernel

**TODO**: Implement 2D convolution

```cpp
#define MAX_FILTER_SIZE 11

// Store filter in constant memory for fast access
__constant__ float c_filter[MAX_FILTER_SIZE * MAX_FILTER_SIZE];

__global__ void convolve2D(const float* input, float* output,
                            int width, int height, int filterSize) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Calculate output position
    //    int col = blockIdx.x * blockDim.x + threadIdx.x;
    //    int row = blockIdx.y * blockDim.y + threadIdx.y;
    
    // 2. Calculate filter radius
    //    int radius = filterSize / 2;
    
    // 3. Check bounds
    //    if (row < height && col < width) {
    
    // 4. Perform convolution
    //    float sum = 0.0f;
    //    for (int fr = 0; fr < filterSize; fr++) {
    //        for (int fc = 0; fc < filterSize; fc++) {
    //            // Calculate input position
    //            int ir = row + fr - radius;
    //            int ic = col + fc - radius;
    //            
    //            // Handle boundaries (clamp to edge)
    //            ir = max(0, min(height - 1, ir));
    //            ic = max(0, min(width - 1, ic));
    //            
    //            // Accumulate
    //            int inputIdx = ir * width + ic;
    //            int filterIdx = fr * filterSize + fc;
    //            sum += input[inputIdx] * c_filter[filterIdx];
    //        }
    //    }
    //    
    //    // 5. Write output
    //    output[row * width + col] = sum;
}
```

#### Step 2: Optimized Version with Shared Memory

```cpp
__global__ void convolve2DTiled(const float* input, float* output,
                                 int width, int height, int filterSize) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Define tile size and halo size
    //    #define TILE_W 16
    //    #define TILE_H 16
    //    int radius = filterSize / 2;
    //    int sharedSize = (TILE_W + 2*radius) * (TILE_H + 2*radius);
    
    // 2. Allocate shared memory for tile + halo
    //    __shared__ float tile[TILE_H + 2*radius][TILE_W + 2*radius];
    
    // 3. Load tile with halo into shared memory
    //    - Each thread loads one or more elements
    //    - Handle boundaries
    
    // 4. Synchronize
    //    __syncthreads();
    
    // 5. Perform convolution using shared memory
    //    - Access c_filter from constant memory
    //    - Access input from shared memory (tile)
    
    // This reduces global memory accesses significantly
}
```

---

## Example 6: Neural Network Forward Pass

### Learning Objectives
- Implement fully connected layers
- Create activation functions
- Handle batch processing
- Chain multiple layers

### Implementation Steps

#### Step 1: Fully Connected Layer

**TODO**: Implement FC layer kernel

```cpp
__global__ void fullyConnectedForward(const float* input, const float* weights,
                                       const float* bias, float* output,
                                       int batchSize, int inputSize, int outputSize) {
    // IMPLEMENTATION GUIDELINE:
    // Input: [batchSize, inputSize]
    // Weights: [inputSize, outputSize]
    // Bias: [outputSize]
    // Output: [batchSize, outputSize]
    
    // 1. Calculate output position
    //    int batch = blockIdx.y;
    //    int out = blockIdx.x * blockDim.x + threadIdx.x;
    
    // 2. Check bounds
    //    if (batch < batchSize && out < outputSize) {
    
    // 3. Compute matrix-vector product for this output neuron
    //    float sum = 0.0f;
    //    for (int i = 0; i < inputSize; i++) {
    //        int inputIdx = batch * inputSize + i;
    //        int weightIdx = i * outputSize + out;
    //        sum += input[inputIdx] * weights[weightIdx];
    //    }
    //    
    //    // 4. Add bias
    //    sum += bias[out];
    //    
    //    // 5. Write output
    //    int outputIdx = batch * outputSize + out;
    //    output[outputIdx] = sum;
}
```

#### Step 2: Activation Functions

**TODO**: Implement ReLU, Sigmoid, Tanh

```cpp
__global__ void relu(float* data, int size) {
    // IMPLEMENTATION GUIDELINE:
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        data[idx] = fmaxf(0.0f, data[idx]);
    }
}

__global__ void sigmoid(float* data, int size) {
    // IMPLEMENTATION GUIDELINE:
    // sigmoid(x) = 1 / (1 + exp(-x))
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        data[idx] = 1.0f / (1.0f + expf(-data[idx]));
    }
}

__global__ void tanh_activation(float* data, int size) {
    // IMPLEMENTATION GUIDELINE:
    // tanh(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        data[idx] = tanhf(data[idx]);
    }
}
```

#### Step 3: Forward Pass Pipeline

```cpp
void forward(float* d_input, float* d_output,
             float* d_w1, float* d_b1, float* d_hidden1,
             float* d_w2, float* d_b2, float* d_hidden2,
             float* d_w3, float* d_b3,
             int batchSize) {
    // IMPLEMENTATION GUIDELINE:
    
    // Layer 1: input (784) -> hidden1 (128) with ReLU
    // TODO: Launch fullyConnectedForward
    // TODO: Launch relu
    
    // Layer 2: hidden1 (128) -> hidden2 (64) with ReLU
    // TODO: Launch fullyConnectedForward
    // TODO: Launch relu
    
    // Layer 3: hidden2 (64) -> output (10) with softmax
    // TODO: Launch fullyConnectedForward
    // TODO: Launch softmax (to be implemented)
}
```

---

## Example 7: Neural Network Backward Pass

### Learning Objectives
- Implement backpropagation
- Compute gradients using chain rule
- Implement gradient descent
- Verify gradients numerically

### Implementation Steps

#### Step 1: Activation Derivatives

**TODO**: Implement derivative kernels

```cpp
__global__ void reluBackward(const float* output, const float* gradOutput,
                              float* gradInput, int size) {
    // IMPLEMENTATION GUIDELINE:
    // ReLU derivative: 1 if x > 0, else 0
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        gradInput[idx] = (output[idx] > 0.0f) ? gradOutput[idx] : 0.0f;
    }
}

__global__ void sigmoidBackward(const float* output, const float* gradOutput,
                                 float* gradInput, int size) {
    // IMPLEMENTATION GUIDELINE:
    // sigmoid'(x) = sigmoid(x) * (1 - sigmoid(x))
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        float sig = output[idx];
        gradInput[idx] = gradOutput[idx] * sig * (1.0f - sig);
    }
}
```

#### Step 2: Fully Connected Backward Pass

**TODO**: Implement FC layer backward pass

```cpp
__global__ void fullyConnectedBackward(
    const float* input,      // [batchSize, inputSize]
    const float* weights,    // [inputSize, outputSize]
    const float* gradOutput, // [batchSize, outputSize]
    float* gradInput,        // [batchSize, inputSize]
    float* gradWeights,      // [inputSize, outputSize]
    float* gradBias,         // [outputSize]
    int batchSize, int inputSize, int outputSize) {
    
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Compute gradInput = gradOutput @ weights^T
    //    - Each thread computes one element of gradInput
    
    // 2. Compute gradWeights = input^T @ gradOutput
    //    - Use atomic operations or separate kernel
    
    // 3. Compute gradBias = sum(gradOutput, axis=0)
    //    - Use atomic operations or reduction kernel
}
```

#### Step 3: Weight Update (SGD)

**TODO**: Implement stochastic gradient descent

```cpp
__global__ void sgdUpdate(float* weights, const float* gradients,
                           int size, float learningRate) {
    // IMPLEMENTATION GUIDELINE:
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        weights[idx] -= learningRate * gradients[idx];
    }
}
```

---

## Example 8: Complete Neural Network

### Learning Objectives
- Build end-to-end training system
- Implement loss functions
- Create training loop
- Load and process datasets
- Evaluate model performance

### Implementation Steps

#### Step 1: Cross-Entropy Loss

**TODO**: Implement cross-entropy loss kernel

```cpp
__global__ void crossEntropyLoss(const float* predictions, const int* labels,
                                   float* loss, int batchSize, int numClasses) {
    // IMPLEMENTATION GUIDELINE:
    // loss = -log(predictions[label])
    
    int batch = blockIdx.x * blockDim.x + threadIdx.x;
    if (batch < batchSize) {
        int label = labels[batch];
        int idx = batch * numClasses + label;
        
        // Avoid log(0)
        float pred = fmaxf(predictions[idx], 1e-7f);
        loss[batch] = -logf(pred);
    }
}

__global__ void crossEntropyGradient(const float* predictions, const int* labels,
                                       float* gradPredictions,
                                       int batchSize, int numClasses) {
    // IMPLEMENTATION GUIDELINE:
    // gradient = predictions - one_hot(labels)
    
    int batch = blockIdx.y;
    int cls = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (batch < batchSize && cls < numClasses) {
        int idx = batch * numClasses + cls;
        int label = labels[batch];
        
        gradPredictions[idx] = predictions[idx];
        if (cls == label) {
            gradPredictions[idx] -= 1.0f;
        }
    }
}
```

#### Step 2: Training Loop

```cpp
void train(/* model parameters */, /* data */, int numEpochs) {
    // IMPLEMENTATION GUIDELINE:
    
    for (int epoch = 0; epoch < numEpochs; epoch++) {
        float epochLoss = 0.0f;
        
        // TODO: Loop over mini-batches
        for (int batch = 0; batch < numBatches; batch++) {
            // 1. Load batch data to GPU
            //    cudaMemcpy(d_input, h_batchInput, ...);
            
            // 2. Forward pass
            //    forward(...);
            
            // 3. Compute loss
            //    crossEntropyLoss<<<...>>>(...);
            
            // 4. Backward pass
            //    crossEntropyGradient<<<...>>>(...);
            //    backward(...);
            
            // 5. Update weights
            //    sgdUpdate<<<...>>>(...);
            
            // 6. Accumulate loss
            //    epochLoss += batchLoss;
        }
        
        // TODO: Evaluate on validation set
        float accuracy = evaluate(/* validation data */);
        
        printf("Epoch %d: Loss=%.4f, Accuracy=%.2f%%\n",
               epoch, epochLoss / numBatches, accuracy * 100);
    }
}
```

#### Step 3: Model Evaluation

```cpp
float evaluate(/* model parameters */, /* test data */) {
    // IMPLEMENTATION GUIDELINE:
    
    int correct = 0;
    int total = 0;
    
    for (int batch = 0; batch < numTestBatches; batch++) {
        // 1. Forward pass (no gradient computation)
        forward(...);
        
        // 2. Get predictions (argmax)
        //    TODO: Implement argmax kernel
        
        // 3. Compare with labels
        //    TODO: Count correct predictions
        
        correct += batchCorrect;
        total += batchSize;
    }
    
    return (float)correct / total;
}
```

#### Step 4: MNIST Data Loading

```cpp
void loadMNIST(const char* imageFile, const char* labelFile,
               float** images, int** labels,
               int* numImages) {
    // IMPLEMENTATION GUIDELINE:
    
    // 1. Read MNIST file header
    //    - Magic number
    //    - Number of images
    //    - Image dimensions (28x28)
    
    // 2. Allocate memory
    //    *images = (float*)malloc(*numImages * 784 * sizeof(float));
    
    // 3. Read and normalize images
    //    for (int i = 0; i < *numImages * 784; i++) {
    //        unsigned char pixel;
    //        fread(&pixel, 1, 1, fp);
    //        (*images)[i] = pixel / 255.0f;  // Normalize to [0, 1]
    //    }
    
    // 4. Read labels
}
```

### Expected Results

After training on MNIST:
- **Epoch 1**: Accuracy ~85%
- **Epoch 5**: Accuracy ~92%
- **Epoch 10**: Accuracy ~95%
- **Epoch 20**: Accuracy ~96-97%

### Performance Optimization Checklist

1. **Memory Management**
   - Use pinned memory for faster transfers
   - Minimize host-device transfers
   - Reuse device memory

2. **Kernel Optimization**
   - Check occupancy with profiler
   - Optimize shared memory usage
   - Avoid divergence

3. **Algorithmic**
   - Use cuBLAS for large matrix multiplications
   - Implement mini-batch processing
   - Consider mixed precision (FP16)

---

## Debugging Tips

### Print Device Variables

```cpp
__global__ void debug_kernel() {
    printf("Block (%d,%d,%d), Thread (%d,%d,%d)\n",
           blockIdx.x, blockIdx.y, blockIdx.z,
           threadIdx.x, threadIdx.y, threadIdx.z);
}
```

### Check for Errors

Always check errors after:
- Memory operations
- Kernel launches
- Synchronization

### Use cuda-gdb

```bash
nvcc -g -G program.cu  # Compile with debug info
cuda-gdb ./program
```

### Profile with Nsight

```bash
# Nsight Compute (kernel profiling)
ncu --set full -o profile ./program

# Nsight Systems (timeline)
nsys profile -o timeline ./program
```

---

## Testing Strategy

### Unit Tests

Test each kernel independently:

```cpp
// test_vector_addition.cu
void testVectorAddition() {
    int N = 1000;
    // TODO: Create test inputs with known outputs
    // TODO: Run kernel
    // TODO: Verify results
    assert(allClose(expected, actual, 1e-5));
}
```

### Integration Tests

Test combinations:

```cpp
// test_forward_pass.cu
void testForwardPass() {
    // TODO: Initialize weights to known values
    // TODO: Run forward pass
    // TODO: Compare with manual computation
}
```

### Gradient Checking

Numerically verify gradients:

```cpp
float numericalGradient(/* ... */) {
    float epsilon = 1e-4;
    float loss1 = computeLoss(param + epsilon);
    float loss2 = computeLoss(param - epsilon);
    return (loss1 - loss2) / (2 * epsilon);
}

void checkGradients() {
    float numerical = numericalGradient(/* ... */);
    float analytical = computeGradient(/* ... */);
    float diff = fabs(numerical - analytical);
    assert(diff < 1e-4);
}
```

---

## Next Steps

After completing all examples:

1. **Optimize Performance**
   - Profile with Nsight
   - Use cuBLAS/cuDNN libraries
   - Implement custom optimizations

2. **Extend Functionality**
   - Add more layer types (Conv2D, Pooling)
   - Implement data augmentation
   - Add learning rate scheduling

3. **Scale Up**
   - Train on larger datasets (CIFAR-10, ImageNet)
   - Implement multi-GPU training
   - Use mixed precision training

4. **Real-World Integration**
   - Export trained models
   - Create inference server
   - Deploy on edge devices

---

## Resources

### CUDA Documentation
- [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA Runtime API](https://docs.nvidia.com/cuda/cuda-runtime-api/)
- [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)

### Deep Learning
- [CS231n: Convolutional Neural Networks](http://cs231n.stanford.edu/)
- [Deep Learning Book](https://www.deeplearningbook.org/)
- [PyTorch CUDA Extensions](https://pytorch.org/tutorials/advanced/cpp_extension.html)

### Performance
- [Nsight Compute Documentation](https://docs.nvidia.com/nsight-compute/)
- [CUDA Optimization Tips](https://developer.nvidia.com/blog/cuda-pro-tip-optimize-gpu-performance/)

Happy CUDA programming!
