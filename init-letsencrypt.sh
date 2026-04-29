#!/bin/bash
# ============================================================
#  First-time Let's Encrypt certificate provisioning
#  Usage: ./init-letsencrypt.sh [domain] [api_domain] [email]
#  Run once on fresh server; certbot container auto-renews after.
# ============================================================
set -euo pipefail

DOMAIN="${1:-clipsgold.ru}"
API_DOMAIN="${2:-api.clipsgold.ru}"
EMAIL="${3:-akamalov781@gmail.com}"
DATA_PATH="./certbot"
STAGING=0  # Set to 1 to test against Let's Encrypt staging (avoids rate limits)

log()  { echo -e "\n\033[1;34m### $1\033[0m"; }
ok()   { echo -e "\033[1;32m    OK: $1\033[0m"; }

# ── 1. Download recommended TLS parameters ───────────────────
if [ ! -e "$DATA_PATH/conf/options-ssl-nginx.conf" ]; then
    log "Downloading recommended TLS parameters..."
    mkdir -p "$DATA_PATH/conf"
    curl -fsSL https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
        -o "$DATA_PATH/conf/options-ssl-nginx.conf"
    curl -fsSL https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem \
        -o "$DATA_PATH/conf/ssl-dhparams.pem"
    ok "TLS params downloaded"
fi

# ── 2. Create temporary self-signed cert so nginx can start ──
log "Creating temporary self-signed certificate for $DOMAIN..."
mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
docker compose run --rm --no-deps --entrypoint \
    "openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
        -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
        -subj '/CN=localhost'" \
    certbot
ok "Temporary certificate created"

# ── 3. Start nginx with the temporary cert ───────────────────
log "Starting nginx..."
docker compose up --force-recreate -d nginx
ok "nginx started"

# Wait for nginx to be ready
sleep 3

# ── 4. Delete temporary cert, request real one ───────────────
log "Deleting temporary certificate..."
docker compose run --rm --no-deps --entrypoint \
    "rm -rf /etc/letsencrypt/live/$DOMAIN \
             /etc/letsencrypt/archive/$DOMAIN \
             /etc/letsencrypt/renewal/$DOMAIN.conf" \
    certbot
ok "Temporary cert removed"

log "Requesting Let's Encrypt certificate for: $DOMAIN www.$DOMAIN $API_DOMAIN"

STAGING_ARG=""
[ "$STAGING" = "1" ] && STAGING_ARG="--staging"

docker compose run --rm --no-deps --entrypoint \
    "certbot certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        $STAGING_ARG \
        -d $DOMAIN \
        -d www.$DOMAIN \
        -d $API_DOMAIN" \
    certbot

ok "Let's Encrypt certificate issued"

# ── 5. Reload nginx with real cert ───────────────────────────
log "Reloading nginx with real certificate..."
docker compose exec nginx nginx -s reload
ok "nginx reloaded"

echo ""
echo "════════════════════════════════════════════"
echo "  SSL ready!"
echo "  Frontend: https://${DOMAIN}"
echo "  API:      https://${API_DOMAIN}"
echo "  Renewal:  certbot container auto-renews every 12h"
echo "════════════════════════════════════════════"
