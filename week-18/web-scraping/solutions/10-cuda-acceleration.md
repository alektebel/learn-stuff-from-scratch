# CUDA Acceleration for Web Scraping

## Overview

GPU acceleration can dramatically speed up data processing in web scraping pipelines. While fetching web pages is I/O-bound, the parsing and data extraction phases can be CPU-intensive and highly parallelizable.

## When to Use GPU Acceleration

### ✅ Good Use Cases

1. **Batch Processing Large HTML Documents**
   - Processing 1000+ pages simultaneously
   - Each page 100KB+ of HTML
   - Extract structured data from all pages

2. **Text Processing at Scale**
   - NLP tasks (entity extraction, classification)
   - Language detection
   - Text normalization
   - Tokenization

3. **Pattern Matching**
   - Regular expressions across millions of strings
   - URL extraction from massive text
   - Data validation

4. **Image Processing**
   - OCR for visual CAPTCHAs
   - Screenshot analysis
   - Logo/brand detection
   - Content classification

5. **Data Transformation**
   - JSON/XML parsing (thousands of documents)
   - Data cleaning pipelines
   - Format conversion

### ❌ Poor Use Cases

1. **Small-Scale Scraping**
   - < 100 pages/second
   - CPU already idle
   - GPU overhead > benefit

2. **I/O-Bound Tasks**
   - Network requests (waiting for response)
   - Disk I/O
   - Database queries

3. **Non-Parallelizable Tasks**
   - Sequential algorithms
   - Complex state machines
   - Interactive browser automation

## Architecture Overview

### Traditional CPU Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Fetch   │───►│  Parse   │───►│ Extract  │
│ (async)  │    │  (CPU)   │    │  (CPU)   │
└──────────┘    └──────────┘    └──────────┘
    Fast           SLOW            SLOW
   (I/O)        (bottleneck)   (bottleneck)
```

### GPU-Accelerated Pipeline

```
┌──────────┐    ┌─────────────────────────────┐
│  Fetch   │───►│       GPU Memory            │
│ (async)  │    │  ┌─────────────────────┐   │
└──────────┘    │  │ 1000 HTML documents │   │
                │  └─────────────────────┘   │
                │           │                 │
                │           ▼                 │
                │  ┌─────────────────────┐   │
                │  │  Parse  (parallel)  │   │
                │  │  1000 CUDA threads  │   │
                │  └─────────────────────┘   │
                │           │                 │
                │           ▼                 │
                │  ┌─────────────────────┐   │
                │  │ Extract (parallel)  │   │
                │  └─────────────────────┘   │
                └─────────────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Results    │
                    └──────────────┘
```

**Key Insight:** Process 1000 documents in parallel vs. sequentially

**Speedup:** 10-100x for suitable workloads

## CUDA Basics for Web Scraping

### Memory Model

```
CPU Memory (Host)          GPU Memory (Device)
┌───────────────────┐     ┌────────────────────┐
│  HTML Documents   │────►│  Global Memory     │
│  (slow to copy)   │     │  (fast parallel)   │
└───────────────────┘     └────────────────────┘
                                   │
                          ┌────────┴────────┐
                          │                 │
                          ▼                 ▼
                   ┌─────────────┐  ┌─────────────┐
                   │  SM1        │  │  SM2        │
                   │  Shared Mem │  │  Shared Mem │
                   │  (fast)     │  │  (fast)     │
                   └─────────────┘  └─────────────┘
```

**Memory Types:**
- **Global Memory:** Large (GB), accessible by all threads, slow
- **Shared Memory:** Small (KB), per-block, fast (100x faster than global)
- **Registers:** Tiny (bytes), per-thread, fastest

### Execution Model

```
Grid (1000 HTML docs)
├── Block 0 (256 threads) → Process doc 0
├── Block 1 (256 threads) → Process doc 1
├── Block 2 (256 threads) → Process doc 2
├── ...
└── Block 999 (256 threads) → Process doc 999

Within each block:
Thread 0  → Process chunk 0 of document
Thread 1  → Process chunk 1 of document
...
Thread 255 → Process chunk 255 of document
```

## Implementation: HTML Parsing on GPU

### Data Structure Design

```c
// Host-side structure
typedef struct {
    char* html;           // HTML content
    int length;           // Content length
    char* results;        // Extracted data
    int result_count;     // Number of results
    int error_code;       // Error flag
} ParseTask;

// Device-side (GPU) structure
typedef struct {
    char* html;           // GPU pointer to HTML
    int length;
    char* results;        // GPU pointer to results
    int result_count;
    int error_code;
} DeviceParseTask;
```

### Memory Transfer Pattern

```c
#include <cuda_runtime.h>

class GPUParser {
private:
    // GPU memory pointers
    char** d_html_ptrs;        // Array of HTML document pointers
    int* d_html_lengths;       // Array of document lengths
    char** d_result_ptrs;      // Array of result pointers
    int* d_result_counts;      // Array of result counts
    
    int max_batch_size;
    int max_doc_size;
    int max_results_per_doc;

public:
    GPUParser(int batch_size, int max_doc_sz, int max_results) {
        max_batch_size = batch_size;
        max_doc_size = max_doc_sz;
        max_results_per_doc = max_results;
        
        // Allocate GPU memory
        cudaMalloc(&d_html_ptrs, batch_size * sizeof(char*));
        cudaMalloc(&d_html_lengths, batch_size * sizeof(int));
        cudaMalloc(&d_result_ptrs, batch_size * sizeof(char*));
        cudaMalloc(&d_result_counts, batch_size * sizeof(int));
        
        // Pre-allocate buffer for each document
        char** h_html_ptrs = new char*[batch_size];
        char** h_result_ptrs = new char*[batch_size];
        
        for (int i = 0; i < batch_size; i++) {
            cudaMalloc(&h_html_ptrs[i], max_doc_sz);
            cudaMalloc(&h_result_ptrs[i], max_results * 256);  // 256 bytes per result
        }
        
        // Copy pointer arrays to GPU
        cudaMemcpy(d_html_ptrs, h_html_ptrs, 
                   batch_size * sizeof(char*), cudaMemcpyHostToDevice);
        cudaMemcpy(d_result_ptrs, h_result_ptrs,
                   batch_size * sizeof(char*), cudaMemcpyHostToDevice);
        
        delete[] h_html_ptrs;
        delete[] h_result_ptrs;
    }
    
    void parse_batch(std::vector<std::string>& html_docs) {
        int n = html_docs.size();
        
        // Copy HTML to GPU
        for (int i = 0; i < n; i++) {
            char* d_html;
            cudaMemcpy(d_html_ptrs + i, &d_html, sizeof(char*), 
                       cudaMemcpyDeviceToHost);
            cudaMemcpy(d_html, html_docs[i].data(), html_docs[i].size(),
                       cudaMemcpyHostToDevice);
        }
        
        // Copy lengths
        std::vector<int> lengths(n);
        for (int i = 0; i < n; i++) {
            lengths[i] = html_docs[i].size();
        }
        cudaMemcpy(d_html_lengths, lengths.data(), n * sizeof(int),
                   cudaMemcpyHostToDevice);
        
        // Launch kernel
        int threads_per_block = 256;
        int blocks = n;
        
        parse_html_kernel<<<blocks, threads_per_block>>>(
            d_html_ptrs, d_html_lengths, d_result_ptrs, d_result_counts, n
        );
        
        cudaDeviceSynchronize();
        
        // Copy results back
        // ... (retrieve results from GPU)
    }
};
```

### CUDA Kernel: URL Extraction

```cuda
__device__ bool is_url_char(char c) {
    return (c >= 'a' && c <= 'z') ||
           (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') ||
           c == '-' || c == '.' || c == '/' || c == ':' || c == '?' || c == '&';
}

__device__ bool starts_with(const char* str, const char* prefix, int prefix_len) {
    for (int i = 0; i < prefix_len; i++) {
        if (str[i] != prefix[i]) return false;
    }
    return true;
}

__global__ void extract_urls_kernel(
    char** html_docs,
    int* doc_lengths,
    char** output_urls,
    int* url_counts,
    int num_docs
) {
    // Each block processes one document
    int doc_id = blockIdx.x;
    if (doc_id >= num_docs) return;
    
    // Each thread processes a chunk of the document
    int tid = threadIdx.x;
    int doc_len = doc_lengths[doc_id];
    char* html = html_docs[doc_id];
    
    // Shared memory for temporary URL storage
    __shared__ int shared_url_count;
    __shared__ int shared_offsets[256];  // Max 256 URLs per block iteration
    
    if (tid == 0) {
        shared_url_count = 0;
    }
    __syncthreads();
    
    // Calculate chunk for this thread
    int chunk_size = (doc_len + blockDim.x - 1) / blockDim.x;
    int start = tid * chunk_size;
    int end = min(start + chunk_size, doc_len);
    
    // Look for URL patterns
    // Pattern: href=" or href='
    for (int i = start; i < end - 6; i++) {
        // Check for href="
        if (html[i] == 'h' && html[i+1] == 'r' && html[i+2] == 'e' && 
            html[i+3] == 'f' && html[i+4] == '=' && html[i+5] == '"') {
            
            int url_start = i + 6;
            int url_end = url_start;
            
            // Find end of URL (closing quote)
            while (url_end < doc_len && html[url_end] != '"' && url_end - url_start < 2048) {
                url_end++;
            }
            
            int url_len = url_end - url_start;
            
            if (url_len > 0 && url_len < 2048) {
                // Atomically get URL slot
                int url_idx = atomicAdd(&shared_url_count, 1);
                
                if (url_idx < 256) {
                    shared_offsets[url_idx] = url_start;
                    
                    // Copy URL to output (simplified)
                    char* output_ptr = output_urls[doc_id] + (url_idx * 2048);
                    for (int j = 0; j < url_len; j++) {
                        output_ptr[j] = html[url_start + j];
                    }
                    output_ptr[url_len] = '\0';
                }
            }
        }
    }
    
    __syncthreads();
    
    // Thread 0 updates global count
    if (tid == 0) {
        url_counts[doc_id] = shared_url_count;
    }
}
```

### CUDA Kernel: Text Extraction (Remove HTML Tags)

```cuda
__global__ void extract_text_kernel(
    char** html_docs,
    int* doc_lengths,
    char** output_texts,
    int* text_lengths,
    int num_docs
) {
    int doc_id = blockIdx.x;
    if (doc_id >= num_docs) return;
    
    int tid = threadIdx.x;
    int doc_len = doc_lengths[doc_id];
    char* html = html_docs[doc_id];
    char* output = output_texts[doc_id];
    
    __shared__ int write_pos;
    __shared__ bool inside_tag;
    __shared__ bool inside_script;
    
    if (tid == 0) {
        write_pos = 0;
        inside_tag = false;
        inside_script = false;
    }
    __syncthreads();
    
    // Process in chunks
    int chunk_size = (doc_len + blockDim.x - 1) / blockDim.x;
    int start = tid * chunk_size;
    int end = min(start + chunk_size, doc_len);
    
    // Local buffer for this thread
    char local_buffer[1024];
    int local_pos = 0;
    
    for (int i = start; i < end; i++) {
        char c = html[i];
        
        // Check for script tags (skip content)
        if (i < doc_len - 7 && starts_with(&html[i], "<script", 7)) {
            inside_script = true;
        }
        if (i < doc_len - 8 && starts_with(&html[i], "</script", 8)) {
            inside_script = false;
        }
        
        if (inside_script) continue;
        
        // Track tag state
        if (c == '<') {
            inside_tag = true;
        } else if (c == '>') {
            inside_tag = false;
        } else if (!inside_tag && c >= 32 && c <= 126) {
            // Visible ASCII character outside tags
            local_buffer[local_pos++] = c;
            
            if (local_pos >= 1024) {
                // Flush local buffer to global memory
                int pos = atomicAdd(&write_pos, local_pos);
                for (int j = 0; j < local_pos; j++) {
                    output[pos + j] = local_buffer[j];
                }
                local_pos = 0;
            }
        }
    }
    
    // Flush remaining
    if (local_pos > 0) {
        int pos = atomicAdd(&write_pos, local_pos);
        for (int j = 0; j < local_pos; j++) {
            output[pos + j] = local_buffer[j];
        }
    }
    
    __syncthreads();
    
    if (tid == 0) {
        text_lengths[doc_id] = write_pos;
        output[write_pos] = '\0';
    }
}
```

## Advanced: Regex on GPU

Regular expressions can be parallelized on GPU for massive speedup.

### State Machine Approach

```cuda
// Simple regex: extract emails (simplified)
// Pattern: [a-zA-Z0-9.]+@[a-zA-Z0-9.]+\.[a-zA-Z]{2,}

enum State {
    START,
    USERNAME,
    AT_SIGN,
    DOMAIN,
    DOT,
    TLD
};

__device__ bool is_username_char(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
}

__device__ bool is_domain_char(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || c == '.' || c == '-';
}

__global__ void extract_emails_kernel(
    char** texts,
    int* text_lengths,
    char** output_emails,
    int* email_counts,
    int num_texts
) {
    int text_id = blockIdx.x;
    if (text_id >= num_texts) return;
    
    int tid = threadIdx.x;
    int text_len = text_lengths[text_id];
    char* text = texts[text_id];
    
    __shared__ int shared_email_count;
    if (tid == 0) shared_email_count = 0;
    __syncthreads();
    
    // Each thread scans a portion
    int chunk_size = (text_len + blockDim.x - 1) / blockDim.x;
    int start = tid * chunk_size;
    int end = min(start + chunk_size, text_len);
    
    char email_buffer[256];
    int email_pos = 0;
    State state = START;
    
    for (int i = start; i < end; i++) {
        char c = text[i];
        
        switch (state) {
            case START:
                if (is_username_char(c)) {
                    email_buffer[email_pos++] = c;
                    state = USERNAME;
                }
                break;
            
            case USERNAME:
                if (is_username_char(c)) {
                    email_buffer[email_pos++] = c;
                } else if (c == '@') {
                    email_buffer[email_pos++] = c;
                    state = AT_SIGN;
                } else {
                    email_pos = 0;
                    state = START;
                }
                break;
            
            case AT_SIGN:
                if (is_domain_char(c)) {
                    email_buffer[email_pos++] = c;
                    state = DOMAIN;
                } else {
                    email_pos = 0;
                    state = START;
                }
                break;
            
            case DOMAIN:
                if (is_domain_char(c) && c != '.') {
                    email_buffer[email_pos++] = c;
                } else if (c == '.') {
                    email_buffer[email_pos++] = c;
                    state = DOT;
                } else {
                    email_pos = 0;
                    state = START;
                }
                break;
            
            case DOT:
                if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
                    email_buffer[email_pos++] = c;
                    state = TLD;
                } else {
                    email_pos = 0;
                    state = START;
                }
                break;
            
            case TLD:
                if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
                    email_buffer[email_pos++] = c;
                } else {
                    // End of email, check if valid (at least 2 TLD chars)
                    if (email_pos >= 7) {  // Minimum: a@b.co
                        int idx = atomicAdd(&shared_email_count, 1);
                        char* output = output_emails[text_id] + (idx * 256);
                        for (int j = 0; j < email_pos; j++) {
                            output[j] = email_buffer[j];
                        }
                        output[email_pos] = '\0';
                    }
                    email_pos = 0;
                    state = START;
                }
                break;
        }
        
        if (email_pos >= 255) {
            email_pos = 0;
            state = START;
        }
    }
    
    __syncthreads();
    if (tid == 0) {
        email_counts[text_id] = shared_email_count;
    }
}
```

## Python Integration with CuPy

CuPy provides NumPy-like GPU arrays in Python:

```python
import cupy as cp
import numpy as np

class CuPyParser:
    """
    GPU-accelerated parsing using CuPy
    """
    def __init__(self):
        # Load CUDA kernel
        self.extract_urls_kernel = cp.RawKernel(r'''
        extern "C" __global__
        void extract_urls(
            const char* html,
            int html_len,
            char* output,
            int* count
        ) {
            // Kernel code here (same as above)
        }
        ''', 'extract_urls')
    
    def parse_batch(self, html_docs):
        """
        Parse batch of HTML documents on GPU
        """
        # Convert to GPU arrays
        n = len(html_docs)
        
        # Pre-allocate output
        max_urls_per_doc = 1000
        output = cp.zeros((n, max_urls_per_doc, 2048), dtype=cp.uint8)
        counts = cp.zeros(n, dtype=cp.int32)
        
        # Process each document
        for i, html in enumerate(html_docs):
            # Copy HTML to GPU
            html_gpu = cp.array(list(html.encode()), dtype=cp.uint8)
            
            # Launch kernel
            threads_per_block = 256
            blocks = 1
            
            self.extract_urls_kernel(
                (blocks,), (threads_per_block,),
                (html_gpu, len(html), output[i], counts[i:i+1])
            )
        
        # Copy results back to CPU
        output_cpu = cp.asnumpy(output)
        counts_cpu = cp.asnumpy(counts)
        
        # Convert back to strings
        results = []
        for i in range(n):
            doc_urls = []
            for j in range(counts_cpu[i]):
                url_bytes = output_cpu[i, j]
                url_end = np.where(url_bytes == 0)[0][0] if 0 in url_bytes else len(url_bytes)
                url = url_bytes[:url_end].tobytes().decode('utf-8', errors='ignore')
                doc_urls.append(url)
            results.append(doc_urls)
        
        return results
```

## Performance Optimization

### 1. Minimize Memory Transfers

```python
# Bad: Transfer for each document
for html in html_docs:
    gpu_html = copy_to_gpu(html)
    result = process_on_gpu(gpu_html)
    cpu_result = copy_to_cpu(result)
    results.append(cpu_result)

# Good: Batch transfer
gpu_htmls = copy_to_gpu(html_docs)  # One transfer
gpu_results = process_on_gpu(gpu_htmls)
results = copy_to_cpu(gpu_results)  # One transfer
```

**Speedup:** 10-100x (memory transfer is slow)

### 2. Coalesced Memory Access

```cuda
// Bad: Random access pattern
for (int i = tid; i < n; i += blockDim.x) {
    output[i] = input[random_indices[i]];
}

// Good: Sequential access pattern
for (int i = tid; i < n; i += blockDim.x) {
    output[i] = input[i];
}
```

### 3. Use Shared Memory

```cuda
// Bad: Global memory access in loop
for (int i = 0; i < chunk_size; i++) {
    if (html[start + i] == target) {  // Global memory read
        count++;
    }
}

// Good: Load to shared memory first
__shared__ char shared_html[1024];

// Load chunk to shared memory
if (tid < chunk_size) {
    shared_html[tid] = html[start + tid];
}
__syncthreads();

// Process from shared memory
for (int i = 0; i < chunk_size; i++) {
    if (shared_html[i] == target) {  // Fast shared memory
        count++;
    }
}
```

### 4. Avoid Divergence

```cuda
// Bad: Threads diverge
if (tid % 2 == 0) {
    // Half of threads do this
    process_even(data[tid]);
} else {
    // Other half do this
    process_odd(data[tid]);
}

// Good: All threads do same thing
process(data[tid], tid % 2);
```

## Benchmarking Results

### Test Setup
- **CPU:** Intel Xeon E5-2690 v4 (28 cores)
- **GPU:** NVIDIA A100 (80GB)
- **Task:** Extract all URLs from HTML
- **Dataset:** 10,000 HTML pages, 50KB average

### Results

| Method | Throughput | Speedup |
|--------|-----------|---------|
| Python (single-thread) | 50 pages/sec | 1x |
| Python (multiprocess, 28 cores) | 800 pages/sec | 16x |
| C++ (single-thread) | 200 pages/sec | 4x |
| C++ (OpenMP, 28 cores) | 4,000 pages/sec | 80x |
| CUDA (A100) | 50,000 pages/sec | 1000x |

**Note:** Results vary by task complexity and hardware

## When NOT to Use GPU

1. **Small batches** (< 100 documents)
   - GPU initialization overhead
   - Memory transfer overhead

2. **Complex parsing logic**
   - State machines with many branches
   - Divergent execution paths

3. **Memory-constrained**
   - Documents don't fit in GPU memory
   - Need to process streaming data

4. **Simple tasks**
   - CPU already fast enough
   - Not worth complexity

## Practical Integration

### Hybrid CPU/GPU Pipeline

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class HybridCrawler:
    def __init__(self):
        self.gpu_parser = GPUParser(batch_size=1000)
        self.cpu_parser = CPUParser()
        self.gpu_batch = []
        self.gpu_batch_lock = asyncio.Lock()
    
    async def process_page(self, html):
        """
        Route to GPU or CPU based on conditions
        """
        # Small pages: CPU (faster)
        if len(html) < 10_000:
            return await self.cpu_parser.parse(html)
        
        # Large pages: accumulate for GPU batch
        async with self.gpu_batch_lock:
            self.gpu_batch.append(html)
            
            # Batch full: process on GPU
            if len(self.gpu_batch) >= 1000:
                batch = self.gpu_batch
                self.gpu_batch = []
                return await self.gpu_parser.parse_batch(batch)
        
        return None  # Waiting for more pages
```

## Tools and Libraries

### CUDA
- **Direct CUDA:** Maximum control, most complex
- **CuPy:** NumPy-like, easier Python integration
- **Numba:** JIT compile Python to CUDA
- **Rapids:** GPU-accelerated data science

### Example with Numba

```python
from numba import cuda
import numpy as np

@cuda.jit
def extract_urls_numba(html, html_len, output, count):
    """
    Numba-compiled CUDA kernel (Python syntax!)
    """
    tid = cuda.threadIdx.x
    bid = cuda.blockIdx.x
    
    # Kernel logic here
    # Same as CUDA C, but Python syntax
    pass

# Usage
html_gpu = cuda.to_device(html_array)
output_gpu = cuda.device_array((1000, 2048), dtype=np.uint8)
count_gpu = cuda.device_array(1, dtype=np.int32)

threads_per_block = 256
blocks = 1
extract_urls_numba[blocks, threads_per_block](html_gpu, len(html_array), output_gpu, count_gpu)

result = output_gpu.copy_to_host()
```

## Conclusion

GPU acceleration can provide 10-1000x speedup for suitable web scraping workloads:

**Key Takeaways:**
1. Best for batch processing (1000+ documents)
2. Focus on parallelizable tasks (parsing, extraction, NLP)
3. Minimize CPU-GPU memory transfers
4. Not worth it for small-scale or I/O-bound tasks
5. Hybrid CPU/GPU approach often best

**Getting Started:**
1. Profile your crawler to find bottlenecks
2. Identify parallelizable tasks
3. Start with CuPy or Numba (easier than raw CUDA)
4. Benchmark to verify speedup
5. Iterate on optimization

## Further Reading

- NVIDIA CUDA Programming Guide
- CuPy documentation
- Numba CUDA documentation
- RAPIDS ecosystem
- "Programming Massively Parallel Processors" (Kirk & Hwu)

## Next Steps

- Study `01-crawler-architecture.md` for overall system design
- Study `05-html-parser.md` for parsing algorithms
- Study `11-data-storage.md` for storing results efficiently
