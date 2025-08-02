FROM caddy:2.7-alpine

# Install additional tools
RUN apk add --no-cache curl openssl

# Create directories for certificates and configuration
RUN mkdir -p /etc/caddy/certs /etc/caddy/config /etc/caddy/data

# Copy Caddyfile
COPY Caddyfile /etc/caddy/Caddyfile

# Copy certificate generation script
COPY generate-certs.sh /usr/local/bin/generate-certs.sh
RUN chmod +x /usr/local/bin/generate-certs.sh

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose ports
EXPOSE 80 443 2019

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:2019/metrics || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]