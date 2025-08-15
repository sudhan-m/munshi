# GCP-specific Terraform-managed values for Munshi pronunciation profiling platform

# Global settings
global:
  imageRegistry: ${artifact_registry_url}
  imagePullPolicy: IfNotPresent

# Environment
environment: ${environment}
namespace: ${namespace}

# Images (using GCP Artifact Registry)
images:
  authService:
    repository: ${artifact_registry_url}/munshi-auth-service
    tag: latest
  uiService:
    repository: ${artifact_registry_url}/munshi-ui-service
    tag: latest
  audioService:
    repository: ${artifact_registry_url}/munshi-audio-service
    tag: latest
  asrService:
    repository: ${artifact_registry_url}/munshi-asr-service
    tag: latest
  llmService:
    repository: ${artifact_registry_url}/munshi-llm-service
    tag: latest
  pronunciationEvaluator:
    repository: ${artifact_registry_url}/munshi-pronunciation-evaluator
    tag: latest
  conversationService:
    repository: ${artifact_registry_url}/munshi-conversation-service
    tag: latest

# Replica counts (managed by Terraform)
replicaCount:
  authService: ${auth_service_replicas}
  uiService: ${ui_service_replicas}
  audioService: ${audio_service_replicas}
  asrService: 2
  llmService: 2
  pronunciationEvaluator: 2
  conversationService: 3

# Resources optimized for pronunciation profiling
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
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"
  audioService:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "300m"
  asrService:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
    nodeSelector:
      workload-type: memory-intensive
    tolerations:
      - key: "workload-type"
        operator: "Equal"
        value: "memory-intensive"
        effect: "NoSchedule"
  llmService:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
    nodeSelector:
      workload-type: memory-intensive
    tolerations:
      - key: "workload-type"
        operator: "Equal"
        value: "memory-intensive"
        effect: "NoSchedule"
  pronunciationEvaluator:
    requests:
      memory: "256Mi"
      cpu: "200m"
    limits:
      memory: "512Mi"
      cpu: "500m"
  conversationService:
    requests:
      memory: "512Mi"
      cpu: "200m"
    limits:
      memory: "1Gi"
      cpu: "500m"

# Service configuration
services:
  authService:
    type: ClusterIP
    port: 8001
  uiService:
    type: ClusterIP
    port: 8002
  audioService:
    type: ClusterIP
    port: 8003
  asrService:
    type: ClusterIP
    port: 8004
  llmService:
    type: ClusterIP
    port: 8005
  pronunciationEvaluator:
    type: ClusterIP
    port: 8006
  conversationService:
    type: ClusterIP
    port: 8007

# Environment variables (GCP-specific with pronunciation profiling)
env:
  authService:
    ENVIRONMENT: "${environment}"
    DEBUG: "false"
    AUTH_SERVICE_HOST: "0.0.0.0"
    AUTH_SERVICE_PORT: "8001"
  uiService:
    ENVIRONMENT: "${environment}"
    DEBUG: "false"
    UI_SERVICE_HOST: "0.0.0.0"
    UI_SERVICE_PORT: "8002"
    PRONUNCIATION_PROFILING_ENABLED: "true"
    CONVERSATION_SERVICE_URL: "http://conversation-service:8007"
  audioService:
    ENVIRONMENT: "${environment}"
    DEBUG: "false"
    AUDIO_SERVICE_HOST: "0.0.0.0"
    AUDIO_SERVICE_PORT: "8003"
    GCS_BUCKET_NAME: "${audio_storage_bucket}"
    GOOGLE_CLOUD_PROJECT: "${project_id}"
  asrService:
    ENVIRONMENT: "${environment}"
    ASR_SERVICE_HOST: "0.0.0.0"
    ASR_SERVICE_PORT: "8004"
    MODEL_STORAGE_BUCKET: "${model_storage_bucket}"
    CLOUD_RUN_MODE: "false"
    GPU_SUPPORT: "cpu"
    FALLBACK_MODE: "true"
  llmService:
    ENVIRONMENT: "${environment}"
    LLM_SERVICE_HOST: "0.0.0.0"
    LLM_SERVICE_PORT: "8005"
    GOOGLE_API_KEY_SECRET: "google-api-keys"
  pronunciationEvaluator:
    ENVIRONMENT: "${environment}"
    EVALUATOR_SERVICE_HOST: "0.0.0.0"
    EVALUATOR_SERVICE_PORT: "8006"
  conversationService:
    ENVIRONMENT: "${environment}"
    CONVERSATION_SERVICE_HOST: "0.0.0.0"
    CONVERSATION_SERVICE_PORT: "8007"
    ASR_SERVICE_URL: "http://asr-service:8004"
    LLM_SERVICE_URL: "http://llm-service:8005"
    EVALUATOR_SERVICE_URL: "http://pronunciation-evaluator:8006"
    AUDIO_SERVICE_URL: "http://audio-service:8003"
    MONGODB_URL_SECRET: "database-credentials"

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
  jwtSecretRef: jwt-secret
  database:
    credentialsRef: database-credentials
  googleApi:
    keysRef: google-api-keys

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