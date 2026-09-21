# Distributed Training from Scratch

This directory contains a from-scratch implementation of distributed training systems for machine learning.

## Goal
Build distributed training systems to understand:
- Data parallelism and model parallelism
- Gradient synchronization and all-reduce algorithms
- Communication protocols (Ring-AllReduce, Parameter Server)
- Fault tolerance and checkpointing
- Multi-GPU and multi-node training
- Distributed optimization strategies

## Learning Path

### Phase 1: Single-Node Multi-GPU (Beginner)
1. **Basic Data Parallel Training**
   - Implement data loading and distribution across GPUs
   - Gradient aggregation with averaging
   - Simple synchronous training loop

2. **Communication Patterns**
   - Implement basic all-reduce operation
   - Compare different reduction strategies
   - Measure communication overhead

### Phase 2: Advanced Single-Node (Intermediate)
3. **Gradient Accumulation**
   - Implement micro-batching
   - Memory-efficient training strategies
   - Mixed precision training

4. **Model Parallelism**
   - Split model across GPUs
   - Pipeline parallelism basics
   - Tensor parallelism for large layers

### Phase 3: Multi-Node Training (Advanced)
5. **Distributed Data Parallel (DDP)**
   - Ring-AllReduce implementation
   - Gradient bucketing and overlapping
   - Network topology awareness

6. **Parameter Server Architecture**
   - Centralized parameter updates
   - Asynchronous vs synchronous updates
   - Load balancing strategies

### Phase 4: Production System (Hero Level)
7. **Fault Tolerance**
   - Checkpointing strategies
   - Automatic recovery from failures
   - Elastic training (adding/removing nodes)

8. **Real-Life Application: Large-Scale Image Classification**
   - Train ResNet/ViT on ImageNet using 8+ GPUs
   - Implement gradient compression
   - Add monitoring and profiling
   - Deploy on cloud infrastructure (AWS/GCP)
   - Achieve competitive training time and accuracy

## Project Structure

```
distributed-training/
├── README.md (this file)
├── phase1_data_parallel/
│   ├── template_data_loader.py (with TODOs and guidelines)
│   ├── template_trainer.py (skeleton with hints)
│   └── guidelines.md (detailed instructions)
├── phase2_advanced/
│   ├── template_gradient_accumulation.py
│   ├── template_model_parallel.py
│   └── guidelines.md
├── phase3_multi_node/
│   ├── template_ring_allreduce.py
│   ├── template_parameter_server.py
│   └── guidelines.md
├── phase4_production/
│   ├── template_fault_tolerance.py
│   ├── template_monitoring.py
│   └── guidelines.md
└── solutions/
    ├── phase1_data_parallel/
    │   ├── data_loader.py (complete implementation)
    │   └── trainer.py
    ├── phase2_advanced/
    │   ├── gradient_accumulation.py
    │   └── model_parallel.py
    ├── phase3_multi_node/
    │   ├── ring_allreduce.py
    │   └── parameter_server.py
    └── phase4_production/
        ├── imagenet_trainer.py (full production system)
        ├── fault_tolerance.py
        ├── monitoring.py
        ├── deployment/
        │   ├── kubernetes.yaml
        │   └── docker-compose.yaml
        └── README.md (how to run the production system)
```

## Getting Started

1. Start with Phase 1 and work through the templates
2. Read the guidelines in each phase directory
3. Try to implement the templates before looking at solutions
4. Test your implementation with small models first
5. Compare your solution with the provided implementations
6. Move to the next phase once you understand the current one

## Prerequisites

- Python 3.8+
- PyTorch or TensorFlow
- CUDA toolkit (for GPU support)
- Understanding of basic neural networks and backpropagation
- Familiarity with Python multiprocessing

## Testing Your Implementation

Each phase includes test scripts to validate your implementation:
```bash
python test_phase1.py  # Test your Phase 1 implementation
python test_phase2.py  # Test your Phase 2 implementation
# etc.
```

## Resources

**Documentation & Guides**:
- [PyTorch Distributed Overview](https://pytorch.org/tutorials/beginner/dist_overview.html)
- [Ring-AllReduce Paper](https://arxiv.org/abs/1509.01916)
- [ZeRO: Memory Optimizations](https://arxiv.org/abs/1910.02054)
- [Megatron-LM](https://github.com/NVIDIA/Megatron-LM)

**Video Courses**:
- [CS 677 - Distributed Operating Systems - UMass](https://www.youtube.com/playlist?list=PLacuG5pysFbBpWHfKUU9Dfdk8RmQ7B9EH)
- [6.824 - Distributed Systems - MIT](https://pdos.csail.mit.edu/6.824/schedule.html)
- [Distributed Systems Courses](https://github.com/Developer-Y/cs-video-courses#distributed-systems)
- [Machine Learning Courses](https://github.com/Developer-Y/cs-video-courses#machine-learning)

## Note

These implementations are for educational purposes. They prioritize clarity and understanding over production-ready performance. The Phase 4 production system demonstrates best practices but may need additional hardening for critical production use.

## Sources

- Goyal et al., **"Accurate, Large Minibatch SGD"**, 2017 — the linear scaling rule and why warmup is needed.
- Li et al., **"PyTorch Distributed"**, VLDB 2020 — gradient bucketing and overlap.
- Rajbhandari et al., **"ZeRO"**, SC 2020 — where the memory actually goes, which is not where people assume.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-8--distributed-training)
