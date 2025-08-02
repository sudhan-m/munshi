#!/bin/sh

# Docker entrypoint script for Nginx with certificate generation

set -e

echo "Starting Nginx with SSL for auth service..."

# Check if certificates exist
if [ ! -f "/etc/nginx/certs/localhost.pem" ] || [ ! -f "/etc/nginx/certs/localhost-key.pem" ]; then
    echo "Certificates not found. Generating development certificates..."
    
    # Check if we're in development mode
    if [ "${ENVIRONMENT:-development}" = "development" ]; then
        echo "Development mode: Generating mkcert certificates..."
        /usr/local/bin/generate-certs.sh
    else
        echo "Production mode: Please provide SSL certificates manually."
        echo "Expected files:"
        echo "  /etc/nginx/certs/localhost.pem"
        echo "  /etc/nginx/certs/localhost-key.pem"
        exit 1
    fi
else
    echo "SSL certificates found."
fi

# Validate nginx configuration
echo "Validating Nginx configuration..."
nginx -t

# Execute the command
echo "Starting Nginx..."
exec "$@"