#!/bin/bash
# Provaani Production — SSL Certificate Auto-Renewal
# Run via cron: 0 4 * * 1 /home/rahul/Provaani_akruti/deploy/renew_ssl.sh >> /var/log/provaani_ssl_renew.log 2>&1
#
# Renews Let's Encrypt certificates and reloads Nginx to pick up the new cert.
# Uses --webroot mode so Nginx stays running (no port 80 conflict).

set -euo pipefail

echo "[$(date)] Starting SSL certificate renewal check..."

# Renew using webroot (Nginx serves /.well-known/acme-challenge from /usr/share/nginx/html)
certbot renew --quiet --no-self-upgrade 2>&1 || true

# Reload Nginx inside the custom-ui container to pick up renewed certificates
docker exec dograhtest-custom-ui nginx -s reload 2>/dev/null && \
  echo "[$(date)] Nginx reloaded with renewed certificates." || \
  echo "[$(date)] Nginx reload skipped (container may not be running)."

echo "[$(date)] SSL renewal check completed."
