# Auth Service Reverse Proxy

A production-ready Nginx reverse proxy for the authentication service with HTTPS termination, security headers, and rate limiting.

## Overview

This reverse proxy provides:

- **HTTPS Termination**: Handles SSL/TLS encryption for secure password transmission
- **Security Headers**: Implements security best practices (HSTS, CSP, etc.)
- **Rate Limiting**: Protects against brute force attacks
- **Request Logging**: Comprehensive access and error logging
- **Health Checks**: Endpoint monitoring and load balancing

## Architecture

```
Client (HTTPS) → Nginx Reverse Proxy → FastAPI Auth Service (HTTP)
                    ↓
                SSL Termination
                Security Headers
                Rate Limiting
```

## Development Setup

### Local HTTPS with mkcert

The development configuration automatically generates local certificates using mkcert:

```bash
# Start with reverse proxy
cd src/auth_service
docker-compose up -d

# Auth service now available at:
# https://localhost (redirects from http://localhost)
# https://auth.localhost
```

### Testing HTTPS Locally

```bash
# Register user over HTTPS
curl -k -X POST "https://localhost/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "TestPass123"
  }'

# Login over HTTPS
curl -k -X POST "https://localhost/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

## Production Deployment

### Option 1: Let's Encrypt (Recommended)

```bash
# Update domain in production.conf
sed -i 's/your-domain.com/your-actual-domain.com/g' nginx/production.conf

# Use production configuration
cp nginx/production.conf nginx/nginx.conf

# Deploy with Let's Encrypt
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Custom Certificates

```bash
# Place your certificates in:
# nginx/certs/your-domain.com.pem
# nginx/certs/your-domain.com-key.pem

# Update nginx.conf to use your certificate paths
# Then deploy
docker-compose up -d
```

## Security Features

### 1. TLS Configuration

- **Protocols**: TLS 1.2 and 1.3 only
- **Ciphers**: Strong cipher suites with perfect forward secrecy
- **HSTS**: Strict Transport Security with preload
- **OCSP Stapling**: Certificate validation (production)

### 2. Security Headers

```nginx
# Prevent clickjacking
add_header X-Frame-Options DENY;

# Prevent MIME sniffing
add_header X-Content-Type-Options nosniff;

# XSS Protection
add_header X-XSS-Protection "1; mode=block";

# Content Security Policy
add_header Content-Security-Policy "default-src 'self'";

# Strict Transport Security
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
```

### 3. Rate Limiting

```nginx
# Protect against brute force attacks
limit_req_zone $binary_remote_addr zone=auth_rate_limit:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=auth_burst_limit:10m rate=30r/m;

# Apply limits
limit_req zone=auth_rate_limit burst=5 nodelay;
limit_req zone=auth_burst_limit burst=10 nodelay;
```

### 4. Request Filtering

- **Body Size Limit**: 1MB maximum request size
- **Admin Endpoints**: Blocked from external access
- **Sensitive Files**: Hidden files blocked
- **Error Pages**: Custom error handling

## Configuration Files

### Development (`nginx.conf`)
- **Purpose**: Local development with mkcert
- **Domain**: localhost, auth.localhost
- **Rate Limiting**: Lenient (10 req/min)
- **Certificates**: Auto-generated mkcert

### Production (`production.conf`)
- **Purpose**: Production deployment
- **Domain**: Configurable (your-domain.com)
- **Rate Limiting**: Strict (5 req/min)
- **Certificates**: Let's Encrypt or custom

## Monitoring

### Health Checks

```bash
# Nginx health
curl -f https://localhost/health

# Certificate expiry check
openssl x509 -in /etc/nginx/certs/localhost.pem -noout -dates
```

### Logs

```bash
# Access logs
docker exec auth-nginx tail -f /var/log/nginx/auth_access.log

# Error logs
docker exec auth-nginx tail -f /var/log/nginx/auth_error.log

# Nginx status
docker exec auth-nginx nginx -t
```

## Troubleshooting

### Certificate Issues

```bash
# Regenerate development certificates
docker exec auth-nginx /usr/local/bin/generate-certs.sh

# Check certificate validity
openssl x509 -in /etc/nginx/certs/localhost.pem -noout -text
```

### Rate Limiting

```bash
# Check rate limit status
docker exec auth-nginx cat /var/log/nginx/auth_error.log | grep "limiting requests"

# Reset rate limiting (restart nginx)
docker restart auth-nginx
```

### SSL/TLS Issues

```bash
# Test SSL configuration
docker exec auth-nginx nginx -t

# Check SSL certificate chain
openssl s_client -connect localhost:443 -servername localhost
```

## Environment Variables

```bash
# Development
ENVIRONMENT=development

# Production
ENVIRONMENT=production
DOMAIN=your-domain.com
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
```

## Performance Tuning

### Production Optimizations

```nginx
# Worker processes
worker_processes auto;

# Connection limits
worker_connections 2048;

# Buffer sizes
proxy_buffer_size 256k;
proxy_buffers 8 256k;

# Compression
gzip on;
gzip_types text/plain application/json;
```

## Security Considerations

1. **Regular Updates**: Keep Nginx and certificates updated
2. **Certificate Monitoring**: Set up expiry alerts
3. **Log Analysis**: Monitor for suspicious patterns
4. **Rate Limit Tuning**: Adjust based on legitimate usage
5. **Firewall Rules**: Restrict access to necessary ports only

This reverse proxy setup ensures that your authentication service can securely handle plaintext passwords over HTTPS while maintaining high security standards and protection against common attacks.