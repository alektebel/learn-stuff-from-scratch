# MLOps from Scratch

This directory contains from-scratch implementations of MLOps practices and tools.

## Goal
Build complete MLOps pipelines to understand:
- Experiment tracking and model registry
- CI/CD for ML models
- Feature engineering pipelines
- Automated model training and deployment
- Model governance and compliance
- Infrastructure as Code for ML

## Learning Path

### Phase 1: Experiment Tracking (Beginner)
1. **Simple Experiment Logger**
   - Track hyperparameters and metrics
   - Save model artifacts
   - Compare experiment results
   - Version datasets

2. **Model Registry**
   - Store trained models with metadata
   - Version control for models
   - Model staging (dev, staging, production)
   - Model lineage tracking

### Phase 2: Automated Pipelines (Intermediate)
3. **Training Pipeline**
   - Automated data preprocessing
   - Hyperparameter tuning
   - Model training and evaluation
   - Automated testing of models

4. **Feature Store**
   - Feature computation and storage
   - Feature versioning
   - Online and offline feature serving
   - Feature monitoring

### Phase 3: CI/CD for ML (Advanced)
5. **Continuous Integration**
   - Automated testing (data, model, infrastructure)
   - Model validation gates
   - Performance benchmarks
   - Security scanning

6. **Continuous Deployment**
   - Automated model deployment
   - Canary deployments
   - Rollback mechanisms
   - Blue-green deployment

### Phase 4: Complete MLOps Platform (Hero Level)
7. **Real-Life Application: End-to-End Credit Scoring System**
   - Automated data pipelines
   - Feature store with real-time features
   - Automated training on schedule and triggers
   - CI/CD pipeline with multiple environments
   - Model monitoring and auto-retraining
   - Compliance and audit logging
   - Deployed on cloud with IaC (Terraform/Pulumi)

## Project Structure

```
mlops/
├── README.md (this file)
├── phase1_tracking/
│   ├── template_experiment_logger.py
│   ├── template_model_registry.py
│   └── guidelines.md
├── phase2_pipelines/
│   ├── template_training_pipeline.py
│   ├── template_feature_store.py
│   └── guidelines.md
├── phase3_cicd/
│   ├── template_ci_tests.py
│   ├── template_deployment.py
│   └── guidelines.md
├── phase4_platform/
│   ├── template_complete_system/
│   └── guidelines.md
└── solutions/
    ├── phase1_tracking/
    │   ├── experiment_logger.py
    │   ├── model_registry.py
    │   └── storage/
    ├── phase2_pipelines/
    │   ├── training_pipeline.py
    │   ├── feature_store.py
    │   └── orchestration/
    ├── phase3_cicd/
    │   ├── ci_pipeline.py
    │   ├── cd_pipeline.py
    │   ├── .github/
    │   │   └── workflows/
    │   └── tests/
    └── phase4_platform/
        ├── credit_scoring_system/
        │   ├── pipelines/
        │   ├── feature_store/
        │   ├── model_registry/
        │   ├── monitoring/
        │   └── deployment/
        ├── infrastructure/
        │   ├── terraform/
        │   └── kubernetes/
        └── README.md
```

## Getting Started

1. Begin with Phase 1 to understand experiment tracking
2. Build incrementally - each phase depends on previous ones
3. Use version control (git) for all code
4. Set up a local ML platform before cloud deployment
5. Focus on automation and reproducibility

## Prerequisites

- Python 3.8+
- Git for version control
- Docker and Kubernetes basics
- Understanding of ML lifecycle
- CI/CD concepts (GitHub Actions, GitLab CI, etc.)
- Basic cloud knowledge (AWS/GCP/Azure)

## Testing Your Implementation

```bash
# Phase 1: Track experiments
python template_experiment_logger.py
python compare_experiments.py

# Phase 2: Run pipeline
python template_training_pipeline.py --config config.yaml

# Phase 3: CI/CD
# Push to git and watch automated tests run
git push origin feature-branch

# Phase 4: Full platform
terraform apply
kubectl apply -f deployment/
```

## Tools and Technologies

### You'll Learn To Use:
- **Experiment Tracking**: MLflow, Weights & Biases concepts
- **Orchestration**: Airflow, Kubeflow concepts
- **Feature Store**: Feast concepts
- **CI/CD**: GitHub Actions, Jenkins
- **Infrastructure**: Terraform, Kubernetes
- **Monitoring**: Prometheus, Grafana, ELK stack

## Resources

**Documentation & Tools**:
- [MLOps Principles](https://ml-ops.org/)
- [Google MLOps Whitepaper](https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Kubeflow](https://www.kubeflow.org/)
- [Feast Feature Store](https://feast.dev/)

**Video Courses**:
- [Machine Learning Engineering for Production (MLOps) - deeplearning.ai](https://www.deeplearning.ai/courses/machine-learning-engineering-for-production-mlops/)
- [Full Stack Deep Learning](https://fullstackdeeplearning.com/)
- [Machine Learning Courses](https://github.com/Developer-Y/cs-video-courses#machine-learning)
- [Software Engineering Courses](https://github.com/Developer-Y/cs-video-courses#software-engineering)

## Key Concepts

### The MLOps Loop
1. **Data** → Collection, validation, versioning
2. **Training** → Experiment tracking, hyperparameter tuning
3. **Validation** → Model testing, performance benchmarks
4. **Deployment** → Automated, versioned, rollback-capable
5. **Monitoring** → Performance, drift, feedback loop
6. **Retraining** → Triggered by drift or schedule

### Best Practices
- Version everything: data, code, models, configs
- Automate testing at all stages
- Make deployments repeatable and rollback-capable
- Monitor models in production continuously
- Document model decisions for governance

## Note

These implementations demonstrate core MLOps concepts. Production MLOps platforms require additional features for security, compliance, multi-tenancy, and enterprise scale.

## Sources

- Sculley et al., NeurIPS 2015 (above) — configuration debt and entanglement.
- Beyer et al., **Site Reliability Engineering** — the operational half.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-18--the-tail)
