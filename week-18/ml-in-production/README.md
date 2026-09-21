# ML in Production from Scratch

This directory contains from-scratch implementations of machine learning systems for production environments.

## Goal
Build production-ready ML systems to understand:
- Model serving and REST APIs
- Real-time inference pipelines
- Model monitoring and observability
- A/B testing and experimentation
- Feature stores and data pipelines
- Model versioning and deployment strategies

## Learning Path

### Phase 1: Basic Model Serving (Beginner)
1. **REST API for Model Serving**
   - Build a simple Flask/FastAPI server
   - Load and serve a trained model
   - Handle input validation and preprocessing
   - Return predictions with proper error handling

2. **Batch Prediction Service**
   - Process large batches of data
   - Implement queuing and async processing
   - Handle failures and retries

### Phase 2: Scalable Serving (Intermediate)
3. **Model Optimization**
   - Model quantization (INT8, FP16)
   - ONNX conversion for faster inference
   - TensorRT optimization
   - Batch inference optimization

4. **Load Balancing and Scaling**
   - Multi-worker serving with Gunicorn/Uvicorn
   - Horizontal scaling with load balancers
   - Auto-scaling based on traffic
   - Caching strategies for predictions

### Phase 3: Production Monitoring (Advanced)
5. **Observability and Monitoring**
   - Logging predictions and performance metrics
   - Prometheus metrics integration
   - Grafana dashboards for visualization
   - Alerting for model degradation

6. **Data Drift Detection**
   - Monitor input distribution changes
   - Detect concept drift
   - Trigger retraining pipelines
   - A/B testing framework

### Phase 4: Complete Production System (Hero Level)
7. **Real-Life Application: E-commerce Recommendation System**
   - Deploy recommendation model at scale
   - Real-time feature computation
   - Multi-stage ranking pipeline
   - A/B testing framework
   - Complete monitoring and alerting
   - Auto-scaling based on traffic patterns
   - Achieve <100ms p99 latency at 10k RPS

## Project Structure

```
ml-in-production/
├── README.md (this file)
├── phase1_basic_serving/
│   ├── template_model_server.py
│   ├── template_batch_processor.py
│   └── guidelines.md
├── phase2_scalable/
│   ├── template_optimization.py
│   ├── template_load_balancing.py
│   └── guidelines.md
├── phase3_monitoring/
│   ├── template_observability.py
│   ├── template_drift_detection.py
│   └── guidelines.md
├── phase4_production/
│   ├── template_recommendation_system/
│   └── guidelines.md
└── solutions/
    ├── phase1_basic_serving/
    │   ├── model_server.py
    │   └── batch_processor.py
    ├── phase2_scalable/
    │   ├── optimized_server.py
    │   └── load_balancer_config/
    ├── phase3_monitoring/
    │   ├── monitored_server.py
    │   ├── prometheus_metrics.py
    │   └── drift_detector.py
    └── phase4_production/
        ├── recommendation_system/
        │   ├── server.py
        │   ├── feature_store.py
        │   ├── ab_testing.py
        │   └── monitoring/
        ├── deployment/
        │   ├── kubernetes/
        │   ├── docker-compose.yml
        │   └── terraform/
        └── README.md
```

## Getting Started

1. Start with Phase 1 to learn basic serving
2. Each phase builds on the previous one
3. Implement templates before checking solutions
4. Test with local models before scaling
5. Use Docker for consistent environments

## Prerequisites

- Python 3.8+
- Flask or FastAPI
- Docker and Docker Compose
- Basic understanding of REST APIs
- Familiarity with ML model deployment

## Testing Your Implementation

```bash
# Phase 1: Basic serving
python template_model_server.py
curl -X POST http://localhost:5000/predict -d '{"data": [1,2,3]}'

# Phase 2: Load testing
locust -f load_test.py --host=http://localhost:5000

# Phase 3: Check metrics
curl http://localhost:9090/metrics

# Phase 4: Full system
docker-compose up
```

## Resources

**Documentation & Guides**:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Model Serving Patterns](https://www.oreilly.com/library/view/building-machine-learning/9781492053187/)
- [Prometheus Monitoring](https://prometheus.io/docs/introduction/overview/)
- [ONNX Runtime](https://onnxruntime.ai/)

**Video Courses**:
- [Full Stack Deep Learning](https://fullstackdeeplearning.com/)
- [Machine Learning Engineering for Production (MLOps) - deeplearning.ai](https://www.deeplearning.ai/courses/machine-learning-engineering-for-production-mlops/)
- [Machine Learning Systems Design](https://github.com/Developer-Y/cs-video-courses#machine-learning)
- [Deep Learning Courses](https://github.com/Developer-Y/cs-video-courses#deep-learning)

## Note

These implementations are for educational purposes. Production systems require additional security, compliance, and reliability features not fully covered here.

## Sources

- Sculley et al., **"Hidden Technical Debt in Machine Learning Systems"**, NeurIPS 2015 — the one paper to read first.
- Breck et al., **"The ML Test Score"**, IEEE Big Data 2017 — what to actually test.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-18--the-tail)
