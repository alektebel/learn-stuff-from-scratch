# Phase 4: Production E-commerce Recommendation System

This is the final phase of the ML in Production learning path - a complete, production-ready recommendation system deployed at scale.

## Project Overview

Build and deploy a real-time recommendation system for an e-commerce platform that:
- Serves personalized product recommendations
- Handles 10,000+ requests per second (RPS)
- Achieves <100ms p99 latency
- Implements A/B testing for model evaluation
- Includes complete monitoring and alerting
- Auto-scales based on traffic

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer (Nginx)                    │
│                    Traffic: ~10k RPS                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐     ┌────▼─────┐    ┌────▼─────┐
   │ Server 1 │     │ Server 2 │    │ Server N │
   │ Model A  │     │ Model A  │    │ Model B  │
   │ (90%)    │     │ (90%)    │    │ (10%)    │
   └────┬─────┘     └────┬─────┘    └────┬─────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Feature Store     │
              │  (Redis + Postgres) │
              └──────────┬──────────┘
                         │
                    ┌────▼─────┐
                    │ Analytics│
                    │ Pipeline │
                    └──────────┘
```

## Features Implemented

### 1. Multi-Stage Ranking Pipeline
- **Candidate Generation**: Retrieve 1000s of potential items (fast)
- **Scoring**: Rank candidates with ML model (accurate)
- **Re-ranking**: Apply business rules and diversity
- **Filtering**: Remove out-of-stock, recently viewed items

### 2. Real-Time Features
- **User Features**: Recent behavior, preferences, demographics
- **Item Features**: Category, price, popularity, ratings
- **Context Features**: Time of day, device type, location
- **Feature Store**: Low-latency feature serving with caching

### 3. A/B Testing Framework
- **Traffic Splitting**: Route X% to model A, Y% to model B
- **Metric Tracking**: CTR, conversion rate, revenue per user
- **Statistical Testing**: Automatic significance testing
- **Rollback**: Automatic rollback if metrics degrade

### 4. Scalability & Performance
- **Model Optimization**: ONNX + quantization for 5x speedup
- **Caching**: Multi-level caching (model predictions, features)
- **Auto-scaling**: Scale based on CPU/latency metrics
- **Load Balancing**: Distribute traffic evenly

### 5. Monitoring & Observability
- **Latency Tracking**: p50, p95, p99 latencies
- **Model Metrics**: Prediction distribution, confidence scores
- **Business Metrics**: CTR, conversion rate, revenue
- **Alerts**: PagerDuty/Slack alerts for anomalies

## Directory Structure

```
phase4_production/
├── README.md (this file)
├── recommendation_system/
│   ├── server.py                    # FastAPI server
│   ├── models/
│   │   ├── candidate_generator.py   # Fast retrieval
│   │   ├── ranker.py                # ML ranking model
│   │   └── reranker.py              # Business logic
│   ├── features/
│   │   ├── feature_store.py         # Feature management
│   │   ├── user_features.py
│   │   ├── item_features.py
│   │   └── context_features.py
│   ├── ab_testing/
│   │   ├── traffic_splitter.py
│   │   ├── metrics_tracker.py
│   │   └── statistical_tests.py
│   ├── monitoring/
│   │   ├── metrics_exporter.py
│   │   ├── logger.py
│   │   └── alerting.py
│   └── utils/
│       ├── cache.py
│       └── config.py
├── deployment/
│   ├── kubernetes/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml              # Horizontal Pod Autoscaler
│   │   ├── redis.yaml
│   │   └── monitoring.yaml
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── nginx.conf
│   └── terraform/
│       ├── main.tf
│       ├── eks_cluster.tf        # AWS EKS
│       └── rds.tf                # Feature store DB
├── tests/
│   ├── load_tests/
│   │   ├── locustfile.py
│   │   └── scenarios.py
│   ├── unit_tests/
│   └── integration_tests/
└── scripts/
    ├── deploy.sh
    ├── rollback.sh
    └── monitor.sh
```

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start services (Redis, Postgres)
docker-compose up -d redis postgres

# Run server
uvicorn recommendation_system.server:app --reload --port 8000

# Test endpoint
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "context": {"device": "mobile"}}'
```

### Load Testing

```bash
# Run load tests with Locust
locust -f tests/load_tests/locustfile.py \
    --host http://localhost:8000 \
    --users 1000 \
    --spawn-rate 10
```

### Production Deployment (Kubernetes)

```bash
# Deploy to Kubernetes
kubectl apply -f deployment/kubernetes/

# Check deployment status
kubectl get pods -l app=recommendation-system

# View logs
kubectl logs -f deployment/recommendation-system

# Access monitoring dashboard
kubectl port-forward svc/grafana 3000:3000
```

## Configuration

### Model Configuration

```yaml
# config/production.yaml

# Model settings
model:
  candidate_generator:
    type: ann  # Approximate Nearest Neighbors
    index_size: 1000000
    candidates: 500
  
  ranker:
    model_path: models/ranker_v2.onnx
    batch_size: 32
    use_quantization: true
  
  reranker:
    diversity_weight: 0.3
    business_rules:
      - filter_out_of_stock
      - filter_recently_viewed

# Feature store
feature_store:
  redis:
    host: redis-service
    port: 6379
    ttl: 3600
  postgres:
    host: postgres-service
    database: features
    pool_size: 20

# Serving
serving:
  workers: 4
  timeout: 1000  # ms
  max_batch_wait: 10  # ms
  
# A/B testing
ab_testing:
  enabled: true
  experiments:
    - name: ranker_v2_vs_v3
      models:
        control: ranker_v2.onnx
        treatment: ranker_v3.onnx
      traffic_split: [90, 10]
      metrics:
        - ctr
        - conversion_rate
        - revenue_per_user

# Monitoring
monitoring:
  prometheus:
    enabled: true
    port: 9090
  grafana:
    enabled: true
    port: 3000
  alerting:
    slack_webhook: ${SLACK_WEBHOOK}
    pagerduty_key: ${PAGERDUTY_KEY}
```

## API Endpoints

### POST /recommend
Get personalized recommendations for a user.

```json
Request:
{
  "user_id": "user123",
  "num_items": 10,
  "context": {
    "device": "mobile",
    "page": "homepage"
  }
}

Response:
{
  "recommendations": [
    {
      "item_id": "item456",
      "score": 0.89,
      "metadata": {
        "title": "Product Name",
        "price": 29.99
      }
    }
  ],
  "model_version": "v2.3.1",
  "latency_ms": 42.3,
  "experiment_id": "ranker_v2_vs_v3_treatment"
}
```

### GET /health
Health check endpoint.

### GET /metrics
Prometheus metrics endpoint.

## Performance Optimization

### 1. Model Optimization
```bash
# Convert PyTorch model to ONNX
python scripts/convert_to_onnx.py \
    --model models/ranker.pth \
    --output models/ranker.onnx

# Quantize model (INT8)
python scripts/quantize_model.py \
    --model models/ranker.onnx \
    --output models/ranker_int8.onnx
```

Results:
- Original PyTorch: 80ms inference
- ONNX: 18ms inference (4.4x faster)
- ONNX + INT8: 12ms inference (6.7x faster)

### 2. Caching Strategy

```python
# Multi-level caching
1. L1: In-memory LRU cache (predictions)
2. L2: Redis cache (features)
3. L3: Database (full feature store)

Cache hit rates:
- Predictions: ~40% (highly personalized)
- User features: ~85% (cached 1 hour)
- Item features: ~95% (cached 24 hours)
```

### 3. Batch Processing
```python
# Dynamic batching
- Wait up to 10ms for requests
- Batch size: 1-32 (adaptive)
- Improves throughput by 3x
```

## Monitoring Dashboards

### Real-Time Metrics
- **Requests/second**: Current RPS
- **Latency**: p50, p95, p99
- **Error rate**: 4xx, 5xx errors
- **Model metrics**: Average score, score distribution

### Business Metrics
- **Click-through rate (CTR)**: Clicks / Impressions
- **Conversion rate**: Purchases / Clicks
- **Revenue per user**: Average revenue from recommendations
- **Average order value (AOV)**

### System Health
- **CPU utilization**: Per pod
- **Memory usage**: Per pod
- **Pod count**: Current vs desired
- **Cache hit rates**: For each cache level

## A/B Testing

### Running an Experiment

```python
# 1. Deploy new model version
kubectl apply -f deployment/kubernetes/ranker_v3.yaml

# 2. Configure experiment
experiments:
  - name: ranker_v2_vs_v3
    models:
      control: ranker_v2.onnx    # 90% traffic
      treatment: ranker_v3.onnx  # 10% traffic
    
# 3. Monitor metrics
# Access dashboard: http://monitoring.example.com/ab-testing

# 4. Automatic decision after 7 days
# If treatment is significantly better: auto-promote
# If treatment is worse: auto-rollback
```

### Statistical Testing
- Minimum sample size: 10,000 users per variant
- Significance level: α = 0.05
- Power: 1-β = 0.80
- Minimum detectable effect: 5% relative improvement

## Auto-Scaling

### Horizontal Pod Autoscaler (HPA)

```yaml
# Scale based on CPU and custom metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_request_latency_p99
      target:
        type: AverageValue
        averageValue: "100"  # 100ms
```

### Scaling Behavior
- Scale up: Add pods if CPU >70% or p99 latency >100ms
- Scale down: Remove pods if CPU <50% and p99 latency <50ms
- Cool down: Wait 3 minutes between scale operations

## Cost Optimization

### Infrastructure Costs
- **Computing**: $5,000/month (20 pods × $250/month)
- **Database**: $1,000/month (RDS for feature store)
- **Caching**: $500/month (Redis ElastiCache)
- **Monitoring**: $300/month (Prometheus, Grafana)
- **Total**: ~$6,800/month

### Cost per Request
- Total requests: ~26B/month (10k RPS)
- Cost per 1M requests: ~$0.26

### Optimization Tips
- Use spot instances for non-critical replicas
- Implement aggressive caching
- Auto-scale down during low traffic hours
- Use CDN for static features

## Troubleshooting

### High Latency
1. Check cache hit rates
2. Profile model inference time
3. Check database query performance
4. Look for network issues

### Low Throughput
1. Increase number of workers
2. Optimize data loading
3. Enable batch processing
4. Check for CPU bottlenecks

### Low CTR/Conversion
1. Review model predictions
2. Check feature freshness
3. Verify business rules aren't too restrictive
4. A/B test against previous model

## Success Metrics

After deploying this system, you should achieve:
- ✅ **Latency**: p99 <100ms
- ✅ **Throughput**: 10k+ RPS
- ✅ **Availability**: 99.9%+ uptime
- ✅ **Business Impact**: 15-20% improvement in CTR
- ✅ **Cost Efficiency**: <$0.30 per 1M requests

## What You'll Learn

1. How to build and deploy real-time ML systems
2. How to optimize for latency and throughput
3. How to implement A/B testing at scale
4. How to monitor and debug production ML systems
5. How to handle high-traffic scenarios
6. How to balance business and ML objectives

## Next Steps

- Implement multi-armed bandits for dynamic exploration
- Add reinforcement learning for long-term optimization
- Build a feedback loop for online learning
- Implement federated learning for privacy
- Expand to multiple regions (global deployment)
- Add more sophisticated ranking models (neural ranking)

## References

- [Netflix Recommendations](https://netflixtechblog.com/netflix-recommendations-beyond-the-5-stars-part-1-55838468f429)
- [Uber's Real-Time ML Platform](https://eng.uber.com/michelangelo/)
- [DoorDash ML Platform](https://doordash.engineering/2020/04/23/doordash-ml-platform/)
- [AWS Personalize](https://aws.amazon.com/personalize/)
