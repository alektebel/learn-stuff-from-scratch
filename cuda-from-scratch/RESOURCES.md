# Resources

External reading for this directory, filed from a link dump. Notes describe the link; they are not summaries of having read it.

## GPU architecture

- [Modal GPU glossary: CUDA device architecture](https://modal.com/gpu-glossary/device-hardware/cuda-device-architecture)
- [Cornell Virtual Workshop: GPU architecture](https://cvw.cac.cornell.edu/gpu-architecture)
- [Stanford CS149: GPU architecture lecture](https://gfxcourses.stanford.edu/cs149/fall25/lecture/gpuarch/)
- [How to Scale Your Model: the GPU chapter](https://jax-ml.github.io/scaling-book/gpus/)
- [MVidia: online visual hardware-basics course](https://blog.adafruit.com/2026/04/06/mvidia-is-an-online-visual-hardware-basics-course/)

## Kernels and optimisation

- [NVIDIA: Optimizing Parallel Reduction in CUDA (Harris)](https://developer.download.nvidia.com/assets/cuda/files/reduction.pdf)
- [cudacodes: softmax kernel walkthrough](https://github.com/Maharshi-Pandya/cudacodes/blob/master/softmax%2FREADME.md)
- [cudacodes: CUDA kernels from scratch](https://github.com/Maharshi-Pandya/cudacodes)
- [Optimizing LayerNorm in CUDA](https://aryagxr.com/blogs/cuda-optimizing-layernorm)
- [LeetCUDA: CUDA kernel exercises](https://github.com/xlite-dev/LeetCUDA)
- [AI performance engineering (cfregly)](https://github.com/cfregly/ai-performance-engineering)

## Courses

- [MLC: Modern GPU Programming for ML Systems](https://mlc.ai/modern-gpu-programming-for-mlsys/)
- [NVIDIA DLI course event](https://sp-events.courses.nvidia.com/dli-india25)

## Classic GPU performance papers

The links arrived truncated, so these are filed by title. Authors and venues are from memory
and **unverified**; check before citing.

- *Better Performance at Lower Occupancy* (Volkov, GTC 2010): ILP instead of occupancy
- *Benchmarking GPUs to Tune Dense Linear Algebra* (Volkov & Demmel, SC 2008)
- *Use registers and multiple outputs per thread on GPU* (UPM course material)
- *Unrolling parallel loops* (Volkov, GTC tutorial)
- *LU, QR and Cholesky Factorizations using Vector Capabilities of GPUs* (Volkov & Demmel, LAPACK Working Note)
- *Understanding Latency Hiding on GPUs* (Volkov, UC Berkeley PhD thesis)
- *A microbenchmark to study GPU performance models* (Volkov, ACM)
- *Parallel Computing Experiences with CUDA* (Garland et al., IEEE Micro 2008)
- *Fitting FFT onto the G80 Architecture* (Volkov & Kazian, UC Berkeley course project)
- *Stencil Computation Optimization and Auto-tuning on State-of-the-Art Multicore Architectures* (Datta et al., SC 2008)
- *Using GPUs to accelerate the bisection algorithm for finding eigenvalues of symmetric tridiagonal matrices* (Volkov & Demmel, UC Berkeley tech report)
- *Building an Efficient Hash Table on the GPU* (Alcantara et al., GPU Computing Gems)
- *Programming inverse memory hierarchy: case of stencils on GPUs* (UPM)

## Numerical linear algebra

- [INT8 sparse QR: Krylov, quantization and preconditioning](https://www.reidatcheson.com/sparse%20linear%20algebra/krylov/quantization/preconditioning/2026/06/30/int8-sparse-qr.html)

## GPU MODE lectures

- [GPU MODE lectures: code, notebooks and slides](https://github.com/gpu-mode/lectures) (Apache-2.0; read at `77a8df4`)
- Lecture-by-lecture map onto this repo: [ROADMAP.md](ROADMAP.md)
- Videos: the GPU MODE YouTube channel (verify URL)
