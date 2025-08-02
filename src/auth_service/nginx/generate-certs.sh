#!/bin/sh

# Generate local certificates for development
# This script creates mkcert certificates for localhost

CERT_DIR="/etc/nginx/certs"

echo "Generating local development certificates..."

# Install local CA
mkcert -install

# Generate certificates for localhost and auth.localhost
mkcert -cert-file ${CERT_DIR}/localhost.pem -key-file ${CERT_DIR}/localhost-key.pem localhost auth.localhost 127.0.0.1 ::1

echo "Certificates generated successfully!"
echo "Certificate: ${CERT_DIR}/localhost.pem"
echo "Private Key: ${CERT_DIR}/localhost-key.pem"

# Set proper permissions
chmod 644 ${CERT_DIR}/localhost.pem
chmod 600 ${CERT_DIR}/localhost-key.pem

echo "Certificate generation complete."