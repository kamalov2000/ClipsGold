#!/bin/bash
# ============================================================
#  ClipsGold — Docker Deploy Script (run from LOCAL machine)
#  Server:  72.56.112.247
#  Domain:  clipsgold.ru  |  api.clipsgold.ru
#  Repo:    github.com/kamalov2000/ClipsGold
# ============================================================
set -euo pipefail

SERVER_IP="72.56.112.247"
SERVER_USER="root"
SERVER="${SERVER_USER}@${SERVER_IP}"
APP_DIR="/opt/ClipsGold"
REPO_URL="https://github.com/kamalov2000/ClipsGold"
DOMAIN="clipsgold.ru"
API_DOMAIN="api.clipsgold.ru"
EMAIL="akamalov781@gmail.com"
ENV_FILE="./.env"

log()  { echo -e "\n\033[1;34m==> $1\033[0m"; }
ok()   { echo -e "\033[1;32m    [OK] $1\033[0m"; }
warn() { echo -e "\033[1;33m    [!!] $1\033[0m"; }
die()  { echo -e "\033[1;31m    [ERROR] $1\033[0m"; exit 1; }

# ── Preflight ─────────────────────────────────────────────────
log "Preflight checks"
[ -f "$ENV_FILE" ] || die ".env not found at $ENV_FILE — copy .env.example and fill it in"
command -v ssh  >/dev/null || die "ssh not found"
command -v scp  >/dev/null || die "scp not found"
ok "Preflight passed"

# ── 1. Upload .env ────────────────────────────────────────────
log "Step 1/7: Uploading .env to server"
scp "$ENV_FILE" "${SERVER}:/tmp/clipsgold.env"
ok ".env uploaded"

# ── 2. Install Docker ─────────────────────────────────────────
log "Step 2/7: Installing Docker on server"
ssh "$SERVER" 'bash -s' << 'ENDDOCKER'
set -e
if docker --version &>/dev/null; then
    echo "Docker already installed: $(docker --version)"
else
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -q ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker && systemctl start docker
    echo "Docker installed: $(docker --version)"
fi
docker compose version || apt-get install -y -q docker-compose-plugin
ENDDOCKER
ok "Docker ready"

# ── 3. Upload code via git archive (no GitHub credentials needed) ──
log "Step 3/7: Uploading application code"
ssh "$SERVER" "mkdir -p '$APP_DIR'"
git archive HEAD | ssh "$SERVER" "tar -x -C '$APP_DIR'"
ok "Code uploaded to $APP_DIR"

# ── 4. Place .env and configure for production ───────────────
log "Step 4/7: Configuring .env on server"
ssh "$SERVER" "
APP_DIR='$APP_DIR'
set -e
cp /tmp/clipsgold.env \"\$APP_DIR/.env\"
rm /tmp/clipsgold.env
echo '.env placed at \$APP_DIR/.env'
"
ok ".env placed"

# ── 5. Build and start core services ─────────────────────────
log "Step 5/7: Building and starting Docker services"
ssh "$SERVER" "
APP_DIR='$APP_DIR'
set -e
cd \"\$APP_DIR\"
mkdir -p certbot/conf certbot/www

# Pull public images, build app images
docker compose pull postgres redis 2>/dev/null || true
docker compose build backend frontend

# Start everything except nginx (needs certs first)
docker compose up -d postgres redis
echo 'Waiting for database...'
sleep 5
docker compose up -d backend celery_worker factory_worker frontend

echo ''
echo 'Waiting for backend to become healthy (max 60s)...'
for i in \$(seq 1 20); do
    if docker compose exec -T backend curl -sf http://localhost:8000/health &>/dev/null 2>&1; then
        echo 'Backend is healthy'
        break
    fi
    printf '  attempt %d/20...\n' \"\$i\"
    sleep 3
done
"
ok "Core services running"

# ── 6. SSL certificates + nginx ──────────────────────────────
log "Step 6/7: Setting up SSL and nginx (Let's Encrypt)"
ssh "$SERVER" "
APP_DIR='$APP_DIR'
DOMAIN='$DOMAIN'
API_DOMAIN='$API_DOMAIN'
EMAIL='$EMAIL'
set -e
cd \"\$APP_DIR\"
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh \"\$DOMAIN\" \"\$API_DOMAIN\" \"\$EMAIL\"
"
ok "SSL and nginx ready"

# ── 7. Verify ─────────────────────────────────────────────────
log "Step 7/7: Verifying deployment"
ssh "$SERVER" "
APP_DIR='$APP_DIR'
set -e
cd \"\$APP_DIR\"
echo ''
docker compose ps
echo ''
echo 'HTTP checks:'
curl -sI https://clipsgold.ru       | head -1 || echo 'clipsgold.ru: no response yet'
curl -sI https://api.clipsgold.ru/health | head -1 || echo 'api.clipsgold.ru: no response yet'
"

# ── Summary ───────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
echo "  DEPLOY COMPLETE"
echo ""
echo "  Frontend:  https://${DOMAIN}"
echo "  API:       https://${API_DOMAIN}"
echo "  API docs:  https://${API_DOMAIN}/docs"
echo "  Flower:    http://${SERVER_IP}:5555"
echo ""
echo "  Useful commands:"
echo "    ssh ${SERVER} 'cd ${APP_DIR} && docker compose ps'"
echo "    ssh ${SERVER} 'cd ${APP_DIR} && docker compose logs -f backend'"
echo "    ssh ${SERVER} 'cd ${APP_DIR} && docker compose logs -f nginx'"
echo "    ssh ${SERVER} 'cd ${APP_DIR} && docker compose restart backend'"
echo "    ssh ${SERVER} 'cd ${APP_DIR} && docker compose restart nginx'  # after backend/frontend recreate if you see 502"
echo "════════════════════════════════════════════════════"
