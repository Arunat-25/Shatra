#!/bin/sh
# Obtain the first Let's Encrypt certificate for DOMAIN (nginx + certbot prod stack).
set -e
cd "$(dirname "$0")/.."

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (command: docker compose)." >&2
  echo "Install: ./scripts/install-compose-v2.sh" >&2
  exit 1
fi

COMPOSE="docker compose -f docker-compose.prod.yml"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

: "${DOMAIN:?Set DOMAIN in .env}"
: "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL in .env}"

echo "Starting stack (nginx HTTP-only until cert exists)..."
$COMPOSE up -d --build nginx app postgres redis

CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
if $COMPOSE run --rm --entrypoint test certbot -f "$CERT_PATH"; then
  echo "Certificate already exists for ${DOMAIN}."
else
  echo "Requesting certificate for ${DOMAIN}..."
  $COMPOSE run --rm --entrypoint certbot certbot certonly \
    --webroot -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$CERTBOT_EMAIL" \
    --agree-tos \
    --no-eff-email
fi

echo "Reloading nginx with HTTPS config..."
$COMPOSE restart nginx

echo "Done. Verify: curl -s https://${DOMAIN}/health"
