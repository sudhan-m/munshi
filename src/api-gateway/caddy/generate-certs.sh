#!/bin/sh

# Generate certificates for mTLS between Gateway and Auth Service

CERT_DIR="/etc/caddy/certs"
DAYS=365

echo "Generating mTLS certificates for Gateway <-> Auth Service communication..."

# Create certificate directory
mkdir -p ${CERT_DIR}

# Generate CA private key
openssl genrsa -out ${CERT_DIR}/ca.key 4096

# Generate CA certificate
openssl req -new -x509 -days ${DAYS} -key ${CERT_DIR}/ca.key -out ${CERT_DIR}/ca.crt -subj "/C=US/ST=CA/L=SF/O=Munshi/OU=Internal CA/CN=munshi-ca"

# Generate Gateway private key
openssl genrsa -out ${CERT_DIR}/gateway.key 2048

# Generate Gateway certificate signing request
openssl req -new -key ${CERT_DIR}/gateway.key -out ${CERT_DIR}/gateway.csr -subj "/C=US/ST=CA/L=SF/O=Munshi/OU=Gateway/CN=api-gateway"

# Generate Gateway certificate signed by CA
openssl x509 -req -days ${DAYS} -in ${CERT_DIR}/gateway.csr -CA ${CERT_DIR}/ca.crt -CAkey ${CERT_DIR}/ca.key -CAcreateserial -out ${CERT_DIR}/gateway.crt

# Generate Auth Service private key
openssl genrsa -out ${CERT_DIR}/auth.key 2048

# Generate Auth Service certificate signing request
openssl req -new -key ${CERT_DIR}/auth.key -out ${CERT_DIR}/auth.csr -subj "/C=US/ST=CA/L=SF/O=Munshi/OU=Auth/CN=auth-service"

# Generate Auth Service certificate signed by CA
openssl x509 -req -days ${DAYS} -in ${CERT_DIR}/auth.csr -CA ${CERT_DIR}/ca.crt -CAkey ${CERT_DIR}/ca.key -CAcreateserial -out ${CERT_DIR}/auth.crt

# Generate client certificate for external access (development)
openssl genrsa -out ${CERT_DIR}/client.key 2048
openssl req -new -key ${CERT_DIR}/client.key -out ${CERT_DIR}/client.csr -subj "/C=US/ST=CA/L=SF/O=Munshi/OU=Client/CN=localhost"
openssl x509 -req -days ${DAYS} -in ${CERT_DIR}/client.csr -CA ${CERT_DIR}/ca.crt -CAkey ${CERT_DIR}/ca.key -CAcreateserial -out ${CERT_DIR}/client.crt

# Set proper permissions
chmod 644 ${CERT_DIR}/*.crt
chmod 600 ${CERT_DIR}/*.key
chmod 644 ${CERT_DIR}/*.csr

# Clean up CSR files
rm -f ${CERT_DIR}/*.csr

echo "Certificate generation complete!"
echo "CA Certificate: ${CERT_DIR}/ca.crt"
echo "Gateway Certificate: ${CERT_DIR}/gateway.crt"
echo "Gateway Private Key: ${CERT_DIR}/gateway.key"
echo "Auth Service Certificate: ${CERT_DIR}/auth.crt"
echo "Auth Service Private Key: ${CERT_DIR}/auth.key"
echo "Client Certificate: ${CERT_DIR}/client.crt"
echo "Client Private Key: ${CERT_DIR}/client.key"