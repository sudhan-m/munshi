# Deployment Guide

Complete deployment guide for the Munshi microservices architecture with Linkerd service mesh, Redis caching, Caddy reverse proxy, advanced rate limiting, and automatic mTLS communication.

## Quick Start

### Production (Kubernetes + Linkerd - Recommended)

```bash
# Deploy with automatic mTLS and observability
./deploy.sh k8s production

# Access services
linkerd viz dashboard                           # Observability dashboard
kubectl port-forward -n munshi svc/caddy-ingress 8443:443  # Application
```

### Development (Local HTTPS)

```bash
# Option 1: Linkerd-compatible (recommended for development)
./deploy.sh docker development

# Option 2: Traditional microservices
docker-compose -f docker-compose.microservices.yml up -d

# Services available at:
# - Application: https://localhost
# - Linkerd Viz: http://localhost:8080 (Option 1 only)
# - Caddy Admin: http://localhost:2019
```

### Single Auth Service (Local HTTPS)

```bash
cd src/auth_service
docker-compose up -d

# Services available at:
# - Auth Service via Caddy: https://localhost
# - Auth Redis Cache: redis://localhost:6380/1
# - Auth PostgreSQL: postgresql://localhost:5433/auth_db
```

## Architecture Overview

### Service Mesh Architecture (Recommended)
```
Internet → NGINX Ingress → Conversation Service → AI Services (ASR, LLM, Evaluator)
           + Service Mesh   + Service Mesh      + Service Mesh
                ↓              ↓                     ↓
        Automatic mTLS    Observability        Service Identity
        Traffic Management Load Balancing     Circuit Breaking
        Distributed Tracing Retries & Timeouts Security
```

### Traditional Architecture
```
Internet → NGINX Reverse Proxy (HTTPS) → Conversation Service → AI Services
                ↓                              ↓                    ↓
        TLS Termination                MongoDB Cache        Model Caching
        Request Tracing              Rate Limiting         GPU Optimization
        Response Compression         Session Management    Performance Tuning
        Emergency DDoS Protection    Circuit Breaker       Error Handling
```

## Redis Cache Requirements

### **Redis Infrastructure**

The Munshi architecture requires two separate Redis instances for optimal performance and security isolation:

#### **Authentication Service Redis (Database 1)**
- **Port**: 6380 (development) / 6379 (production with network isolation)
- **Database**: 1
- **Memory Requirements**: 256MB minimum, 512MB recommended
- **Persistence**: RDB snapshots for failed login tracking
- **Features**:
  - JWT token blacklisting
  - User session caching (1-hour TTL)
  - Failed login attempt tracking (15-minute sliding window)
  - Account lockout management (15-minute TTL)

#### **Application Cache Redis (Database 0)**
- **Port**: 6381 (development) / 6379 (production with network isolation)
- **Database**: 0
- **Memory Requirements**: 512MB minimum, 1GB recommended
- **Persistence**: RDB + AOF for data integrity
- **Features**:
  - ASR model caching (long TTL)
  - LLM response caching (5-10 minute TTL)
  - Conversation context caching (1-hour TTL)
  - Service health status caching

### **Redis Configuration**

#### **Development Configuration (redis.conf)**
```redis
# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_redis_password
protected-mode yes

# Performance
tcp-keepalive 300
timeout 300
```

#### **Production Configuration**
```redis
# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence (critical for rate limiting)
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Security
requirepass strong_redis_password_change_in_production
protected-mode yes
bind 127.0.0.1 ::1

# Performance optimization
tcp-keepalive 300
timeout 300
tcp-backlog 511
databases 16
```

### **Redis Monitoring**

#### **Health Checks**
```bash
# Test Redis connectivity
redis-cli -h localhost -p 6380 -a password ping
redis-cli -h localhost -p 6381 -a password ping

# Check memory usage
redis-cli -h localhost -p 6380 info memory
redis-cli -h localhost -p 6381 info memory

# Monitor cache hit rates
redis-cli -h localhost -p 6381 info stats | grep cache
```

#### **Performance Metrics**
- **Hit Rate**: Target >95% for authentication cache, >80% for response cache
- **Memory Usage**: Should not exceed 80% of allocated memory
- **Connection Count**: Monitor for connection leaks
- **Eviction Rate**: Should be minimal with proper TTL management

## Deployment Options

### 1. Development Environment

**Features:**
- Automatic HTTPS with Caddy internal CA
- Redis-powered advanced rate limiting (1000-5000 req/min based on auth status)
- Response caching for improved performance (5-10 min TTL)
- JWT token blacklisting for secure logout
- mTLS between Gateway and Auth Service
- Failed login tracking and account lockout protection
- Debug logging enabled
- Hot reload for development

**Setup:**
```bash
git clone <repository>
cd munshi

# Start all services with Caddy ingress
docker-compose -f docker-compose.microservices.yml up -d

# Verify services
curl -k https://localhost/health
curl http://localhost:2019/metrics  # Caddy admin
```

**Environment Variables (.env):**
```bash
# Common Settings
ENVIRONMENT=development
DEBUG=true

# Auth Service Configuration
AUTH_DATABASE_URL=postgresql://auth_user:auth_password@auth-postgres:5432/auth_db
AUTH_REDIS_URL=redis://auth-redis:6379/1
JWT_SECRET_KEY=development_secret_key_change_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=15

# API Gateway Configuration
GATEWAY_DATABASE_URL=postgresql://gateway_user:gateway_password@gateway-postgres:5432/gateway_db
GATEWAY_REDIS_URL=redis://gateway-redis:6379/0
AUTH_SERVICE_URL=https://auth-service:8001
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT_REQUESTS=1000
AUTHENTICATED_RATE_LIMIT_REQUESTS=5000
```

### 2. Production Environment

**Features:**
- Let's Encrypt SSL certificates with automatic renewal
- Enhanced Redis-based rate limiting with production thresholds
- Response caching for optimal performance
- Production security headers and HSTS enforcement
- Comprehensive logging with request correlation
- Health monitoring and metrics collection
- Redis persistence for cache durability
- Connection pooling optimization

**Setup:**
```bash
# Update domain configuration
sed -i 's/your-domain.com/yourdomain.com/g' src/auth_service/nginx/production.conf

# Copy production config
cp src/auth_service/nginx/production.conf src/auth_service/nginx/nginx.conf

# Set production environment
export ENVIRONMENT=production
export DOMAIN=yourdomain.com

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

**Environment Variables (.env.prod):**
```bash
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=strong_random_production_secret_key_64_chars_minimum
AUTH_DATABASE_URL=postgresql://auth_user:secure_password@auth-postgres:5432/auth_db
DOMAIN=yourdomain.com
SSL_EMAIL=admin@yourdomain.com
```

### 3. Cloud Deployment (AWS/GCP/Azure)

**Prerequisites:**
- Container registry (Docker Hub, ECR, GCR)
- Load balancer with SSL termination
- Managed database (RDS, Cloud SQL)
- Container orchestration (ECS, GKE, AKS)

**Example AWS ECS Deployment:**
```bash
# Build and push images
docker build -t your-registry/auth-service:latest src/auth_service/
docker build -t your-registry/auth-nginx:latest src/auth_service/nginx/
docker push your-registry/auth-service:latest
docker push your-registry/auth-nginx:latest

# Deploy with ECS task definition
aws ecs create-service --cluster munshi-cluster --service-name auth-service
```

## SSL Certificate Management

### Development (mkcert)

Automatically handled by the Nginx container:

```bash
# Certificates generated on container start
docker logs auth-nginx

# Manual certificate generation
docker exec auth-nginx /usr/local/bin/generate-certs.sh
```

### Production (Let's Encrypt)

**Option 1: Certbot Integration**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificates
sudo certbot --nginx -d yourdomain.com -d auth.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

**Option 2: Docker Certbot**
```yaml
# Add to docker-compose.yml
certbot:
  image: certbot/certbot
  volumes:
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  command: certonly --webroot -w /var/www/certbot --email admin@yourdomain.com -d yourdomain.com --agree-tos
```

### Production (Custom Certificates)

```bash
# Place certificates in nginx/certs/
cp your-domain.crt src/auth_service/nginx/certs/
cp your-domain.key src/auth_service/nginx/certs/

# Update nginx configuration
# ssl_certificate /etc/nginx/certs/your-domain.crt;
# ssl_certificate_key /etc/nginx/certs/your-domain.key;
```

## Security Configuration

### Nginx Security Headers

```nginx
# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# CSP
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'" always;

# XSS Protection
add_header X-XSS-Protection "1; mode=block" always;

# Frame Options
add_header X-Frame-Options DENY always;

# Content Type Options
add_header X-Content-Type-Options nosniff always;
```

### Rate Limiting

```nginx
# Define rate limits
limit_req_zone $binary_remote_addr zone=auth_rate_limit:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=auth_burst_limit:10m rate=20r/m;

# Apply rate limits
limit_req zone=auth_rate_limit burst=3 nodelay;
limit_req zone=auth_burst_limit burst=5 nodelay;
```

### Firewall Rules

```bash
# UFW configuration
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8001/tcp   # Block direct access to FastAPI
sudo ufw enable
```

## Monitoring and Logging

### Health Checks

```bash
# Auth service health
curl -f https://yourdomain.com/health

# Nginx status
docker exec auth-nginx nginx -t

# Database connectivity
docker exec auth-service curl -f http://localhost:8001/health
```

### Log Monitoring

```bash
# Nginx access logs
docker logs auth-nginx

# Application logs
docker logs auth-service

# Real-time monitoring
docker logs -f auth-nginx auth-service
```

### Metrics Collection

**Prometheus Configuration:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'auth-service'
    static_configs:
      - targets: ['auth-service:8001']
    metrics_path: '/metrics'
```

## Backup and Recovery

### Database Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec auth-postgres pg_dump -U auth_user auth_db > backup_auth_$DATE.sql

# Restore
docker exec -i auth-postgres psql -U auth_user auth_db < backup_auth_$DATE.sql
```

### Configuration Backup

```bash
# Backup configuration
tar -czf munshi_config_$(date +%Y%m%d).tar.gz \
  src/auth_service/nginx/ \
  .env* \
  docker-compose*.yml
```

## Scaling and Load Balancing

### Horizontal Scaling

```yaml
# docker-compose.yml
auth-service:
  deploy:
    replicas: 3
  
nginx:
  depends_on:
    - auth-service
```

### Load Balancer Configuration

```nginx
upstream auth_backend {
    server auth-service-1:8001;
    server auth-service-2:8001;
    server auth-service-3:8001;
}
```

## Troubleshooting

### Common Issues

**1. Certificate Problems**
```bash
# Check certificate validity
openssl x509 -in /etc/nginx/certs/localhost.pem -noout -dates

# Regenerate certificates
docker exec auth-nginx /usr/local/bin/generate-certs.sh
```

**2. Rate Limiting Issues**
```bash
# Check rate limit logs
docker logs auth-nginx | grep "limiting requests"

# Temporarily disable rate limiting
# Comment out limit_req lines in nginx.conf
```

**3. Database Connection**
```bash
# Test database connectivity
docker exec auth-service python -c "
import psycopg2
conn = psycopg2.connect('postgresql://auth_user:auth_password@auth-postgres:5432/auth_db')
print('Database connection successful')
"
```

**4. SSL/TLS Issues**
```bash
# Test SSL configuration
openssl s_client -connect localhost:443 -servername localhost

# Check cipher suites
nmap --script ssl-enum-ciphers -p 443 localhost
```

## Performance Optimization

### Nginx Tuning

```nginx
# Worker optimization
worker_processes auto;
worker_connections 2048;

# Buffer optimization
proxy_buffer_size 256k;
proxy_buffers 8 256k;
proxy_busy_buffers_size 256k;

# Compression
gzip on;
gzip_types text/plain application/json;
```

### Database Optimization

```sql
-- Add indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at);
```

## Security Hardening

### Container Security

```dockerfile
# Use non-root user
RUN addgroup -g 1001 -S appuser && \
    adduser -u 1001 -S appuser -G appuser
USER appuser
```

### Network Security

```bash
# Create isolated networks
docker network create --driver bridge auth-network
docker network create --driver bridge gateway-network
```

### Secret Management

```bash
# Use Docker secrets
echo "strong_jwt_secret" | docker secret create jwt_secret -
echo "db_password" | docker secret create db_password -
```

This deployment guide provides comprehensive instructions for deploying the Munshi microservices architecture with secure HTTPS authentication in various environments.