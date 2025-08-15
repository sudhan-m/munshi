# GCP-specific Terraform-managed values for Munshi Helm chart

# Global settings
global:
  imageRegistry: ${image_registry}
  imagePullPolicy: IfNotPresent

# Environment
environment: ${environment}
namespace: munshi-prod

# Images (using GCP Container Registry)
images:
  authService:
    repository: ${image_registry}/${project_id}/munshi/auth-service
    tag: latest
  uiService:
    repository: ${image_registry}/${project_id}/ui-service
    tag: latest
  audioService:
    repository: ${image_registry}/${project_id}/munshi/audio-service
    tag: v3
  asrService:
    repository: ${image_registry}/${project_id}/munshi/asr-service
    tag: latest
  llmService:
    repository: ${image_registry}/${project_id}/munshi/llm-service
    tag: latest
  pronunciationEvaluator:
    repository: ${image_registry}/${project_id}/munshi/pronunciation-evaluator
    tag: latest
  conversationService:
    repository: ${image_registry}/${project_id}/munshi/conversation-service
    tag: latest

# Replica counts (managed by Terraform)
replicaCount:
  authService: ${auth_service_replicas}
  uiService: ${ui_service_replicas}
  audioService: ${audio_service_replicas}
  postgres: 1
  redis: 1
  mongodb: 1

# Resources
resources:
  authService:
    requests:
      memory: "128Mi"
      cpu: "50m"
    limits:
      memory: "256Mi"
      cpu: "200m"
  uiService:
    requests:
      memory: "128Mi"
      cpu: "50m"
    limits:
      memory: "256Mi"
      cpu: "200m"
  postgres:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "300m"
  redis:
    requests:
      memory: "64Mi"
      cpu: "50m"
    limits:
      memory: "128Mi"
      cpu: "100m"
  audioService:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "300m"
  mongodb:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "300m"

# Service configuration
services:
  authService:
    type: ClusterIP
    port: 8001
  uiService:
    type: ClusterIP
    port: 8002
  postgres:
    port: 5432
  redis:
    port: 6379
  audioService:
    type: ClusterIP
    port: 8003
  mongodb:
    port: 27017

# Environment variables (GCP-specific)
env:
  authService:
    ENVIRONMENT: "${environment}"
    DEBUG: "false"
    AUTH_SERVICE_HOST: "0.0.0.0"
    AUTH_SERVICE_PORT: "8001"
    %{ if cloud_sql_instance != "" }
    POSTGRES_HOST: "/cloudsql/${cloud_sql_instance}"
    %{ endif }
  uiService:
    ENVIRONMENT: "${environment}"
    DEBUG: "false"
    UI_SERVICE_HOST: "0.0.0.0"
    UI_SERVICE_PORT: "8002"
    REAL_TIME_FEEDBACK_ENABLED: "true"
    OFFLINE_MODE_ENABLED: "false"
    ANALYTICS_ENABLED: "true"
  audioService:
    ENVIRONMENT: "${environment}"
    DEBUG: "false"
    AUDIO_SERVICE_HOST: "0.0.0.0"
    AUDIO_SERVICE_PORT: "8003"
    GCS_BUCKET_NAME: "${gcs_bucket_name}"
    GOOGLE_CLOUD_PROJECT: "${project_id}"

# Security
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL

# GCP-specific service account for Workload Identity
serviceAccount:
  create: false
  name: ${workload_service_account}
  annotations:
    iam.gke.io/gcp-service-account: munshi-workload@${project_id}.iam.gserviceaccount.com

# Secrets (references to Terraform-managed secrets)
secrets:
  jwtSecretRef: ${jwt_secret_name}
  postgres:
    authSecretRef: ${postgres_auth_secret_name}
    gatewaySecretRef: ${postgres_gateway_secret_name}
  mongodb:
    secretRef: ${mongodb_secret_name}

# Health checks
healthcheck:
  authService:
    livenessProbe:
      httpGet:
        path: /health
        port: 8001
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health
        port: 8001
      initialDelaySeconds: 5
      periodSeconds: 5
  uiService:
    livenessProbe:
      httpGet:
        path: /health
        port: 8002
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health
        port: 8002
      initialDelaySeconds: 5
      periodSeconds: 5
  audioService:
    livenessProbe:
      httpGet:
        path: /health
        port: 8003
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health
        port: 8003
      initialDelaySeconds: 5
      periodSeconds: 5

# Ingress (GCP-specific)
ingress:
  enabled: true
  className: "gce"
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "munshi-ip"
    networking.gke.io/managed-certificates: "munshi-ssl-cert"
    kubernetes.io/ingress.allow-http: "false"
  hosts:
    - host: munshi.example.com
      paths:
        - path: /
          pathType: Prefix
          service: ui-service
        - path: /api
          pathType: Prefix
          service: api-gateway
  tls:
    - secretName: munshi-tls
      hosts:
        - munshi.example.com

# Autoscaling (HPA managed by Terraform)
autoscaling:
  uiService:
    enabled: false

# Linkerd service mesh
linkerd:
  enabled: true
  controlPlane:
    identity:
      issuer:
        crtExpiry: 2160h
    proxy:
      resources:
        cpu:
          request: "20m"
          limit: "200m"
        memory:
          request: "30Mi"
          limit: "100Mi"
  viz:
    enabled: true
    dashboard:
      enabled: true
      externalUrl: ""
    prometheus:
      enabled: true
    grafana:
      enabled: true
  inject:
    default: enabled

# Monitoring (GCP-specific)
monitoring:
  enabled: true
  stackdriver:
    enabled: true
    projectId: "${project_id}"
  prometheus:
    enabled: false
  grafana:
    enabled: false

# Storage (GCP-specific)
storage:
  audioService:
    size: "10Gi"
    storageClass: "${storage_class}"
  mongodb:
    size: "5Gi"
    storageClass: "${storage_class}"

# GCP-specific configurations
gcp:
  cloudSql:
    enabled: ${cloud_sql_instance != "" ? "true" : "false"}
    %{ if cloud_sql_instance != "" }
    instanceConnectionName: "${cloud_sql_instance}"
    %{ endif }
  cloudStorage:
    bucketName: "${gcs_bucket_name}"
  workloadIdentity:
    enabled: true
    serviceAccount: ${workload_service_account}