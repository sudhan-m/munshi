# ASR Service - Kubernetes GPU with Scale-to-Zero

High-performance GPU-accelerated ASR service that scales to zero when idle for cost optimization.

## 🚀 Features

- **GPU Acceleration**: NVIDIA T4 GPUs for 5-10x faster inference
- **Scale-to-Zero**: Automatically scales down to 0 replicas when idle
- **Your Original Models**: Uses your preferred high-accuracy models
- **Cost Optimized**: Only pay for GPU time when processing requests
- **Auto-scaling**: KEDA-based scaling with multiple triggers
- **Full Monitoring**: GPU metrics, performance monitoring, alerting

## 🔧 Architecture

### GPU Models Used
```
GPU Mode (K8s):
├── English: openai/whisper-large-v2
├── Tamil: vasista22/whisper-tamil-large-v2  
└── Malayalam: thennal/whisper-medium-ml

Fallback (if GPU unavailable):
└── All languages: openai/whisper-base
```

### Scaling Strategy
- **Scale to 0**: When no requests for 30 seconds
- **Scale up**: On incoming HTTP requests (KEDA trigger)
- **Max instances**: 5 replicas for high load
- **GPU allocation**: 1 NVIDIA T4 per pod

## 🛠️ Quick Deployment

### Prerequisites
```bash
# Install required tools
gcloud auth login
kubectl version
docker --version

# Set environment variables
export PROJECT_ID="your-gcp-project-id"
export CLUSTER_NAME="munshi-cluster"
export ZONE="us-central1-a"
```

### One-Command Deploy
```bash
chmod +x deploy-k8s-gpu.sh
./deploy-k8s-gpu.sh
```

This script will:
1. Create GPU node pool with NVIDIA T4
2. Install NVIDIA drivers and KEDA
3. Build and push GPU-optimized Docker image
4. Deploy ASR service with scale-to-zero
5. Set up monitoring and alerting

## 📊 Cost Analysis

### GPU Instance Costs (GKE)
| Instance Type | GPU | vCPU | Memory | Cost/Hour |
|---------------|-----|------|--------|-----------|
| n1-standard-4 | T4 | 4 | 15GB | ~$0.60 |
| n1-standard-8 | T4 | 8 | 30GB | ~$0.90 |

### Example Monthly Costs
| Usage Pattern | Hours/Month | Cost |
|---------------|-------------|------|
| 10 requests/day, 5min each | ~2.5 hours | $1.50 |
| 100 requests/day, 5min each | ~25 hours | $15 |
| 1000 requests/day, 5min each | ~250 hours | $150 |

**Scale-to-zero savings**: 70-90% cost reduction vs always-on GPU instances

## 🔍 Monitoring

### Key Metrics
- **GPU Utilization**: NVIDIA DCGM metrics
- **Request Rate**: HTTP requests per second
- **Response Time**: 95th percentile latency
- **Scaling Events**: Pod creation/deletion
- **Memory Usage**: GPU and system memory

### Dashboards
Access Grafana dashboard: `kubectl port-forward service/grafana 3000:3000`

### Alerts
- High GPU utilization (>90%)
- High memory usage (>85%)
- Service downtime
- Scale-to-zero with pending requests

## 🧪 Testing

### Health Check
```bash
# Port forward to local machine
kubectl port-forward service/asr-service-gpu 8004:8004

# Test health endpoint
curl http://localhost:8004/health
```

### Test Transcription
```bash
# Upload audio file
curl -X POST http://localhost:8004/transcribe \
  -F "audio=@test.wav" \
  -F "language=English"
```

### Load Testing
```bash
# Install hey for load testing
go install github.com/rakyll/hey@latest

# Test scaling behavior
hey -n 100 -c 10 http://localhost:8004/health
```

## 📈 Performance Comparison

| Metric | CPU (Cloud Run) | GPU (K8s) | Improvement |
|--------|-----------------|-----------|-------------|
| Cold Start | 2-5 seconds | 10-15 seconds | - |
| Inference Speed | 15-30 seconds | 2-5 seconds | 5-10x faster |
| Accuracy | Base models | Large models | Higher |
| Cost (light load) | $2-5/month | $10-20/month | 2-4x higher |
| Cost (heavy load) | $30-50/month | $50-100/month | Similar |

## 🔧 Configuration

### Environment Variables
```yaml
CLOUD_RUN_MODE: false
FALLBACK_MODE: false  
GPU_SUPPORT: cuda
MODEL_CACHE_SIZE: 3
CUDA_VISIBLE_DEVICES: 0
```

### Resource Limits
```yaml
requests:
  memory: 8Gi
  cpu: 2000m
  nvidia.com/gpu: 1
limits:
  memory: 16Gi
  cpu: 4000m
  nvidia.com/gpu: 1
```

## 🔒 Security

### GPU Node Security
- GPU nodes are tainted to prevent non-GPU workloads
- Network policies restrict inter-pod communication
- Service accounts with minimal required permissions
- Container security contexts with non-root users (where possible)

### Data Handling
- Audio files processed in memory
- Temporary files cleaned up after processing
- No persistent storage of user data
- Model cache isolated per pod

## 🛠️ Troubleshooting

### Common Issues

1. **Pods stuck in Pending**
   ```bash
   # Check GPU node availability
   kubectl describe nodes -l accelerator=nvidia-tesla-t4
   
   # Check node pool scaling
   gcloud container node-pools describe asr-gpu-pool --cluster=munshi-cluster --zone=us-central1-a
   ```

2. **GPU Not Detected**
   ```bash
   # Check NVIDIA driver installation
   kubectl get daemonset nvidia-driver-installer -n kube-system
   
   # Check GPU device plugin
   kubectl get daemonset nvidia-gpu-device-plugin -n kube-system
   ```

3. **High GPU Memory Usage**
   ```bash
   # Check GPU metrics
   kubectl get --raw /api/v1/nodes/NODE_NAME/proxy/metrics/cadvisor | grep gpu
   
   # Restart pods to clear GPU memory
   kubectl rollout restart deployment/asr-service-gpu
   ```

4. **Scaling Issues**
   ```bash
   # Check KEDA scaler status
   kubectl get scaledobject asr-service-gpu-scaler
   
   # Check HPA status
   kubectl get hpa
   
   # Manual scaling for testing
   kubectl scale deployment asr-service-gpu --replicas=1
   ```

### Debug Commands
```bash
# Pod logs
kubectl logs -l app=asr-service-gpu -f

# GPU usage
kubectl top nodes -l accelerator=nvidia-tesla-t4

# KEDA logs
kubectl logs -n keda-system -l app=keda-operator

# Node events
kubectl get events --sort-by=.metadata.creationTimestamp
```

## 🚀 Performance Optimization

### GPU Memory Optimization
1. **Model caching**: Cache 3 models in GPU memory
2. **Batch processing**: Process multiple requests together
3. **Memory monitoring**: Automatic cleanup when pressure detected

### Scaling Optimization
1. **Pre-warming**: Keep 1 replica warm during business hours
2. **Request batching**: Queue requests for better GPU utilization
3. **Health checks**: Optimized probes for faster readiness

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy ASR GPU Service
on:
  push:
    branches: [main]
    paths: ['services/asr-service/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Deploy to K8s
      run: |
        cd services/asr-service
        ./deploy-k8s-gpu.sh
```

## 📝 Maintenance

### Regular Tasks
- Monitor GPU utilization and costs
- Update NVIDIA drivers quarterly
- Review scaling metrics and adjust thresholds
- Update models as new versions are released

### Cost Optimization
- Set appropriate max replicas based on traffic
- Use preemptible GPU nodes for development
- Monitor and alert on unexpected scaling events
- Regular cost analysis and optimization

## 🤝 Support

For issues:
1. Check logs: `kubectl logs -l app=asr-service-gpu`
2. Verify GPU availability: `kubectl describe nodes`
3. Check scaling status: `kubectl get scaledobject`
4. Review monitoring dashboards

## 🎯 Next Steps

1. **Production Setup**: Configure proper monitoring and alerting
2. **Cost Monitoring**: Set up billing alerts and cost tracking  
3. **Performance Tuning**: Optimize model loading and caching
4. **Security Hardening**: Implement network policies and RBAC

Your ASR service now has the best of both worlds: GPU performance when needed, zero cost when idle! 🚀