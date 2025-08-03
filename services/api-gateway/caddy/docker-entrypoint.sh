#!/bin/sh

# Docker entrypoint script for Caddy with mTLS certificate generation

set -e

echo "Starting Caddy API Gateway with mTLS..."

# Check if certificates exist
if [ ! -f "/etc/caddy/certs/ca.crt" ] || [ ! -f "/etc/caddy/certs/gateway.crt" ] || [ ! -f "/etc/caddy/certs/auth.crt" ]; then
    echo "Certificates not found. Generating mTLS certificates..."
    /usr/local/bin/generate-certs.sh
else
    echo "mTLS certificates found."
fi

# Validate Caddyfile
echo "Validating Caddyfile..."
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# Wait for dependent services to be ready
echo "Waiting for API Gateway service to be ready..."
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -f http://api-gateway:8000/health >/dev/null 2>&1; then
        echo "API Gateway service is ready"
        break
    fi
    echo "Waiting for API Gateway service... ($timeout seconds left)"
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo "Warning: API Gateway service not responding, starting Caddy anyway"
fi

# Execute the command
echo "Starting Caddy..."
exec "$@"