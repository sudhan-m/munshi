# Munshi Terraform Infrastructure for Google Cloud Platform

This directory contains Terraform configuration files for deploying the Munshi microservices infrastructure on Google Cloud Platform using Google Kubernetes Engine (GKE).

## Prerequisites

- Terraform >= 1.0
- Google Cloud SDK (gcloud) installed and configured
- kubectl configured for your GKE cluster
- Helm 3.x installed
- A GCP project with billing enabled

## GCP Services Used

- **Google Kubernetes Engine (GKE)** - Container orchestration
- **Google Cloud SQL** - Managed PostgreSQL database
- **Google Cloud Storage** - Object storage for audio files
- **Google Container Registry/Artifact Registry** - Container image storage
- **Google IAM** - Identity and access management with Workload Identity

## Files

- `main-gcp.tf` - Main Terraform configuration for GCP
- `variables-gcp.tf` - GCP-specific variable definitions
- `values-gcp.yaml.tpl` - GCP-optimized Helm values template
- `terraform-gcp.tfvars.example` - Example variables file for GCP

## Setup Instructions

### 1. GCP Project Setup

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Set default project
gcloud config set project $PROJECT_ID
```

### 2. Create GKE Cluster (if not exists)

```bash
# Create a GKE cluster with Workload Identity enabled
gcloud container clusters create munshi-gke-cluster \
    --zone us-central1-a \
    --machine-type e2-medium \
    --num-nodes 3 \
    --enable-autorepair \
    --enable-autoupgrade \
    --enable-ip-alias \
    --workload-pool=$PROJECT_ID.svc.id.goog

# Get cluster credentials
gcloud container clusters get-credentials munshi-gke-cluster --zone us-central1-a
```

### 3. Terraform Configuration

```bash
# Copy the example variables file
cp terraform-gcp.tfvars.example terraform.tfvars

# Edit with your values
vi terraform.tfvars
```

### 4. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="terraform.tfvars"

# Apply configuration
terraform apply -var-file="terraform.tfvars"
```

## GCP-Specific Features

### Workload Identity

The configuration sets up Workload Identity to securely access GCP services:

- Creates a GCP service account `munshi-workload`
- Grants access to Cloud Storage for audio files
- Binds Kubernetes service account to GCP service account
- No need to store service account keys in pods

### Cloud SQL Integration

When `use_cloud_sql = true`:

- Creates a Cloud SQL PostgreSQL instance
- Configures private IP connectivity
- Enables automated backups and point-in-time recovery
- Sets up proper IAM permissions

### Cloud Storage

- Creates a GCS bucket for audio file storage
- Configures lifecycle policies for cost optimization
- Sets up proper IAM bindings for service access

### Security Best Practices

```bash
# Use Secret Manager for sensitive data
gcloud secrets create jwt-secret --data-file=jwt-secret.txt
gcloud secrets create postgres-auth-password --data-file=postgres-auth.txt

# Grant access to secrets
gcloud secrets add-iam-policy-binding jwt-secret \
    --member="serviceAccount:munshi-workload@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Environment Variables for Secrets

Instead of storing secrets in terraform.tfvars, use environment variables:

```bash
export TF_VAR_project_id="your-gcp-project-id"
export TF_VAR_jwt_secret="your-jwt-secret"
export TF_VAR_postgres_auth_password="your-postgres-password"
export TF_VAR_postgres_gateway_password="your-gateway-password"
export TF_VAR_mongodb_password="your-mongodb-password"
```

## Monitoring and Observability

### Google Cloud Monitoring

The configuration enables Google Cloud Monitoring integration:

```yaml
monitoring:
  enabled: true
  stackdriver:
    enabled: true
    projectId: "your-project-id"
```

### Linkerd Service Mesh

Access the Linkerd dashboard:

```bash
kubectl port-forward -n linkerd-viz deploy/web 8084:8084
# Open http://localhost:8084
```

## Cost Optimization

### Development Environment

For development, use smaller instance types:

```hcl
postgres_tier = "db-f1-micro"
storage_class = "standard-rwo"
```

### Production Environment

For production, use performance-optimized settings:

```hcl
postgres_tier = "db-n1-standard-2"
storage_class = "ssd"
use_cloud_sql = true
```

### Storage Lifecycle

The GCS bucket automatically:
- Moves files to Coldline storage after 30 days
- Deletes files after 90 days
- Adjust in `main-gcp.tf` as needed

## Networking

### Private GKE Cluster (Recommended)

For enhanced security, create a private GKE cluster:

```bash
gcloud container clusters create munshi-private-cluster \
    --zone us-central1-a \
    --enable-private-nodes \
    --master-ipv4-cidr-block 172.16.0.0/28 \
    --enable-ip-alias \
    --cluster-ipv4-cidr 10.1.0.0/16 \
    --services-ipv4-cidr 10.2.0.0/16
```

### Ingress

The configuration uses Google Cloud Load Balancer:

```yaml
ingress:
  enabled: true
  className: "gce"
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "munshi-ip"
```

Reserve a static IP:

```bash
gcloud compute addresses create munshi-ip --global
```

## SSL/TLS

Set up managed SSL certificates:

```bash
# Create managed certificate
kubectl apply -f - <<EOF
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: munshi-ssl-cert
  namespace: munshi-prod
spec:
  domains:
    - munshi.example.com
EOF
```

## Troubleshooting

### Common Issues

1. **Workload Identity not working**
   ```bash
   # Check service account binding
   gcloud iam service-accounts get-iam-policy munshi-workload@$PROJECT_ID.iam.gserviceaccount.com
   
   # Verify pod has correct annotation
   kubectl describe pod <pod-name> -n munshi-prod
   ```

2. **Cloud SQL connection issues**
   ```bash
   # Check Cloud SQL proxy
   kubectl logs <pod-name> -c cloudsql-proxy -n munshi-prod
   ```

3. **Storage access issues**
   ```bash
   # Test GCS access from pod
   kubectl exec -it <pod-name> -n munshi-prod -- gsutil ls gs://your-bucket-name
   ```

### Debugging Commands

```bash
# Check GKE cluster status
gcloud container clusters describe munshi-gke-cluster --zone us-central1-a

# View Cloud SQL instances
gcloud sql instances list

# Check GCS buckets
gsutil ls -p $PROJECT_ID

# View service accounts
gcloud iam service-accounts list
```

## Cleanup

To destroy all resources:

```bash
terraform destroy -var-file="terraform.tfvars"

# Clean up GKE cluster if created manually
gcloud container clusters delete munshi-gke-cluster --zone us-central1-a
```

## Integration with CI/CD

### Cloud Build Example

```yaml
steps:
- name: 'hashicorp/terraform:latest'
  entrypoint: 'sh'
  args:
  - '-c'
  - |
    cd infrastructure/terraform
    terraform init
    terraform plan -var="project_id=$PROJECT_ID"
    terraform apply -auto-approve -var="project_id=$PROJECT_ID"
```

### GitHub Actions with Workload Identity

```yaml
- uses: 'google-github-actions/auth@v1'
  with:
    workload_identity_provider: 'projects/123456789/locations/global/workloadIdentityPools/my-pool/providers/my-provider'
    service_account: 'my-service-account@my-project.iam.gserviceaccount.com'

- name: 'Set up Cloud SDK'
  uses: 'google-github-actions/setup-gcloud@v1'

- name: 'Deploy with Terraform'
  run: |
    cd infrastructure/terraform
    terraform init
    terraform apply -auto-approve
```

## Best Practices

1. **Use separate projects for different environments**
2. **Enable audit logging**
3. **Use private GKE clusters**
4. **Implement proper RBAC**
5. **Monitor costs with budgets and alerts**
6. **Use managed certificates for SSL**
7. **Enable network policies**
8. **Use Workload Identity instead of service account keys**