#!/bin/sh
set -e

CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"

if [ ! -f "$CERT_PATH" ]; then
    echo "No TLS cert at ${CERT_PATH} — HTTP-only bootstrap (run scripts/init-letsencrypt.sh after DNS is ready)"
    envsubst '${DOMAIN}' < /etc/nginx/snippets/http-only.conf.template > /etc/nginx/conf.d/default.conf
fi

# Pick up renewed certs without restarting the container (certbot updates shared volume).
(
    while :; do
        sleep 12h
        nginx -s reload 2>/dev/null || true
    done
) &
