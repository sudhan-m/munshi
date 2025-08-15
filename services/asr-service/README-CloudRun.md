# ASR Service - Cloud Run Deployment

Cloud Run optimized version of the ASR (Automatic Speech Recognition) service using Whisper models.

## 🚀 Features

- **Cost-optimized**: Scales to zero when idle, pay only for actual usage
- **Fast cold starts**: Pre-downloaded tiny models, optimized container layers
- **Dynamic model selection**: Automatically chooses best model based on available resources
- **Memory management**: Intelligent memory monitoring and garbage collection
- **Multi-language support**: English, Tamil, Malayalam with fallback strategies

## 📦 Cloud Run Optimizations

### Model Strategy
- **Tiny models** for fastest cold starts (1-2 seconds)
- **Dynamic selection** based on available memory
- **Intelligent caching** with automatic cleanup
- **Fallback mechanisms** for reliability

### Resource Management
- **Memory monitoring** with pressure detection
- **Configurable limits** based on container size
- **Automatic garbage collection** when needed
- **Optimized PyTorch threading** for Cloud Run CPUs

### Performance Tuning
- **Greedy search** for speed in Cloud Run mode
- **Reduced inference complexity** for fast responses
- **Efficient temporary file handling**
- **Comprehensive logging** for monitoring

## 🛠️ Deployment

### Prerequisites
```bash
# Install Google Cloud SDK
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

### Quick Deploy
```bash
# Make script executable
chmod +x deploy-cloudrun.sh

# Set your project ID
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Deploy
./deploy-cloudrun.sh
```

### Manual Deployment
```bash
# Build and push image
gcloud builds submit --tag gcr.io/$PROJECT_ID/asr-service --file Dockerfile.cloudrun .

# Deploy to Cloud Run
gcloud run deploy asr-service \
    --image gcr.io/$PROJECT_ID/asr-service \
    --platform managed \
    --region us-central1 \
    --memory 4Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10 \
    --min-instances 0 \
    --concurrency 1 \
    --allow-unauthenticated
```

## 🔧 Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `CLOUD_RUN_MODE` | `true` | Enable Cloud Run optimizations |
| `FALLBACK_MODE` | `true` | Use smaller models for reliability |
| `GPU_SUPPORT` | `cpu` | Device type (cpu/cuda/metal) |
| `MODEL_CACHE_SIZE` | `1` | Number of models to cache |
| `PORT` | `8080` | Server port (set by Cloud Run) |

### Memory Allocation
- **2GB**: Minimum for tiny models
- **4GB**: Recommended for base models  
- **8GB**: For better accuracy models
- **16GB**: For large models (development only)

## 📊 Cost Optimization

### Expected Costs (us-central1)
- **CPU**: ~$0.000024 per vCPU-second
- **Memory**: ~$0.0000025 per GiB-second
- **Requests**: $0.40 per million requests

### Example Usage Costs
| Requests/Day | Avg Duration | Monthly Cost |
|--------------|--------------|--------------|
| 10 | 30s | $1-2 |
| 100 | 30s | $5-8 |
| 1000 | 30s | $30-50 |

### Cost Reduction Tips
1. **Use tiny models** for English-only applications
2. **Set min-instances=0** to scale to zero
3. **Optimize audio file sizes** (< 5MB recommended)
4. **Monitor cold start frequency**

## 🧪 Testing

### Health Check
```bash
curl https://YOUR_SERVICE_URL/health
```

### Test Transcription
```bash
curl -X POST https://YOUR_SERVICE_URL/transcribe \
  -F "audio=@test.wav" \
  -F "language=English"
```

### Load Testing
```bash
# Install wrk for load testing
brew install wrk

# Test with concurrent requests
wrk -t4 -c10 -d30s https://YOUR_SERVICE_URL/health
```

## 📈 Monitoring

### Cloud Run Metrics
- **Request count** and **latency**
- **Memory usage** and **CPU utilization**  
- **Error rates** and **cold starts**
- **Instance count** and **scaling events**

### Application Logs
```bash
# View recent logs
gcloud run logs read asr-service --region=us-central1

# Follow logs
gcloud run logs tail asr-service --region=us-central1
```

### Key Metrics to Monitor
- **Cold start frequency** (should be < 10% for good UX)
- **Memory pressure** events
- **Model loading times**
- **Request processing duration**

## 🔍 Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory metrics in health endpoint
   curl https://YOUR_SERVICE_URL/health | jq '.memory_status'
   ```

2. **Slow Cold Starts**
   - Verify tiny models are being used
   - Check container image size
   - Review model pre-downloading

3. **Transcription Errors**
   - Validate audio file format
   - Check file size limits
   - Review supported languages

4. **Timeouts**
   - Audio files too large
   - Insufficient memory allocation
   - Model loading issues

### Debug Commands
```bash
# Check service status
gcloud run services describe asr-service --region=us-central1

# Review configuration
gcloud run revisions describe asr-service-XXXX --region=us-central1

# Scale manually for testing
gcloud run services update asr-service --min-instances=1 --region=us-central1
```

## 🔒 Security

### IAM and Permissions
- Service runs with minimal required permissions
- No external network access except for model downloads
- Temporary files cleaned up after processing

### Data Handling
- Audio files processed in memory when possible
- Temporary files have restricted access
- No persistent storage of user data

## 🚀 Performance Tips

1. **Warm Instances**: Set min-instances=1 for production
2. **Optimize Audio**: Use WAV format, 16kHz sample rate
3. **Batch Processing**: Process multiple files when possible
4. **Monitor Scaling**: Adjust max-instances based on traffic

## 📝 API Documentation

Once deployed, visit `https://YOUR_SERVICE_URL/docs` for interactive API documentation.

## 🤝 Contributing

See the main project README for contribution guidelines.