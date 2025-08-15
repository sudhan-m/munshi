# Munshi Cost Optimization Guide

## **Estimated Monthly Cost: $12-18 for 25 hours/month**

### **Cost Breakdown with Optimizations:**

1. **GKE Cluster**: $8-12/month
   - 2 x e2-small preemptible/spot nodes (1 vCPU, 2GB RAM each)
   - 20GB standard disks per node
   - ~60-90% cheaper than regular instances

2. **Cloud Storage**: $1-3/month
   - Audio files with aggressive lifecycle policies
   - Auto-deletion after 90 days

3. **Container Registry**: $1-2/month
   - Image storage only

4. **Networking**: $2-3/month
   - Basic load balancer and egress

## **Key Cost Optimizations Applied:**

### **Infrastructure Level:**
- ✅ **Preemptible/Spot instances** (60-90% cheaper)
- ✅ **Smaller machine types** (e2-small vs e2-medium)
- ✅ **Reduced node count** (2 vs 3 nodes)
- ✅ **Standard disks** (vs SSD)
- ✅ **Smaller disk size** (20GB vs 100GB)
- ✅ **No Cloud SQL** (in-cluster PostgreSQL)

### **Application Level:**
- ✅ **Single replicas** for all services
- ✅ **Reduced resource requests/limits**
- ✅ **Disabled monitoring/analytics**
- ✅ **Disabled Linkerd service mesh**
- ✅ **Relaxed health checks**
- ✅ **Minimal storage sizes**

### **Helm Chart Optimizations:**
- ✅ **In-cluster databases** (PostgreSQL, Redis, MongoDB)
- ✅ **Aggressive GCS lifecycle policies**
- ✅ **Preemptible node affinity**
- ✅ **Minimal HPA settings**
- ✅ **Development-focused configuration**

## **Usage Pattern Management:**

### **For 25 hours/month usage:**

1. **Auto-shutdown script** (save ~50% more):
```bash
#!/bin/bash
# Stop cluster when not in use
gcloud container clusters resize munshi-gke-cluster --num-nodes=0 --zone=us-central1-a --quiet

# Start cluster when needed
# gcloud container clusters resize munshi-gke-cluster --num-nodes=2 --zone=us-central1-a --quiet
```

2. **Scheduled scaling** with Cloud Scheduler:
```bash
# Scale down at night (cron: 0 22 * * *)
gcloud scheduler jobs create http scale-down \
    --schedule="0 22 * * *" \
    --uri="https://container.googleapis.com/v1/projects/central-list-469110-f1/zones/us-central1-a/clusters/munshi-gke-cluster/nodePools/munshi-gke-cluster-node-pool" \
    --http-method=PUT \
    --message-body='{"nodeCount": 0}'

# Scale up in morning (cron: 0 8 * * 1-5)
gcloud scheduler jobs create http scale-up \
    --schedule="0 8 * * 1-5" \
    --uri="https://container.googleapis.com/v1/projects/central-list-469110-f1/zones/us-central1-a/clusters/munshi-gke-cluster/nodePools/munshi-gke-cluster-node-pool" \
    --http-method=PUT \
    --message-body='{"nodeCount": 2}'
```

## **Cost Monitoring Commands:**

```bash
# Check current GKE costs
gcloud billing projects describe central-list-469110-f1

# Monitor resource usage
kubectl top nodes
kubectl top pods -A

# Check preemptible instance status
kubectl get nodes -l cloud.google.com/gke-preemptible=true

# View storage usage
gsutil du -sh gs://central-list-469110-f1-munshi-audio/

# Estimate monthly costs
gcloud alpha billing budgets list
```

## **Emergency Cost Controls:**

### **If costs exceed budget:**

1. **Immediate actions:**
```bash
# Scale down to zero nodes
gcloud container clusters resize munshi-gke-cluster --num-nodes=0 --zone=us-central1-a

# Delete unused storage
gsutil rm -r gs://central-list-469110-f1-munshi-audio/old-files/

# Stop Cloud SQL if enabled
gcloud sql instances patch munshi-postgres --activation-policy=NEVER
```

2. **Set up billing alerts:**
```bash
# Create budget alert at $15/month
gcloud alpha billing budgets create \
    --billing-account=YOUR-BILLING-ACCOUNT \
    --display-name="Munshi Budget Alert" \
    --budget-amount=15USD \
    --threshold-rules=0.8,0.9,1.0
```

## **Deployment Commands:**

```bash
# Deploy cost-optimized configuration
export TF_VAR_jwt_secret="munshi-jwt-$(openssl rand -hex 16)"
export TF_VAR_postgres_auth_password="$(openssl rand -base64 16)"
export TF_VAR_postgres_gateway_password="$(openssl rand -base64 16)"
export TF_VAR_mongodb_password="$(openssl rand -base64 16)"

terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## **Performance vs Cost Trade-offs:**

| Feature | Production | Cost-Optimized | Savings |
|---------|------------|----------------|---------|
| Node Type | n1-standard-2 | e2-small preemptible | 80-90% |
| Replicas | 2-3 per service | 1 per service | 50-70% |
| Monitoring | Full stack | Minimal | 100% |
| Cloud SQL | Managed | In-cluster | 100% |
| Storage | Premium SSD | Standard HDD | 60% |
| Auto-scaling | Aggressive | Conservative | 30% |

## **Scaling Back to Production:**

When ready for production, update `terraform.tfvars`:

```hcl
environment = "production"
use_cloud_sql = true
postgres_tier = "db-n1-standard-1"
machine_type = "e2-standard-2"
node_count = 3
auth_service_replicas = 2
ui_service_replicas = 2
audio_service_replicas = 2
```

**Estimated production cost**: $80-120/month