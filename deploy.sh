#!/bin/bash
# ============================================================
#  ClipsGold — Full Server Deploy Script
#  Server: 216.57.106.48 | User: root
#  DB: SQLite | Queue: FastAPI only (no Celery)
# ============================================================
set -e

SERVER_IP="216.57.106.48"
APP_DIR="/opt/ClipsGold"
REPO_URL="https://github.com/kamalov2000/ClipsGold"
BACKEND_PORT="8000"
FRONTEND_PORT="3000"

log() { echo -e "\n\033[1;34m==> $1\033[0m"; }
ok()  { echo -e "\033[1;32m    [OK] $1\033[0m"; }
warn(){ echo -e "\033[1;33m    [!!] $1\033[0m"; }

# ── 1. Swap 2 GB ─────────────────────────────────────────────
log "Step 1/10: Adding 2 GB swap"
if [ -f /swapfile ]; then
    warn "Swap already exists, skipping"
else
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    ok "Swap 2 GB created and mounted"
fi
free -h

# ── 2. System update & base packages ────────────────────────
log "Step 2/10: Updating system & installing base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -q
apt-get install -y -q \
    git curl wget build-essential software-properties-common \
    libssl-dev libffi-dev libbz2-dev libreadline-dev libsqlite3-dev \
    zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
    ca-certificates gnupg lsb-release
ok "Base packages installed"

# ── 3. Python 3.12 ──────────────────────────────────────────
log "Step 3/10: Installing Python 3.12"
if python3.12 --version &>/dev/null; then
    warn "Python 3.12 already installed: $(python3.12 --version)"
else
    add-apt-repository ppa:deadsnakes/ppa -y
    apt-get update -y -q
    apt-get install -y -q python3.12 python3.12-venv python3.12-dev python3-pip
    ok "Python 3.12 installed"
fi
python3.12 --version

# ── 4. Node.js 20 ───────────────────────────────────────────
log "Step 4/10: Installing Node.js 20"
if node --version 2>/dev/null | grep -q "v20"; then
    warn "Node.js 20 already installed: $(node --version)"
else
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -q nodejs
    ok "Node.js installed: $(node --version)"
fi
node --version && npm --version

# ── 5. FFmpeg ────────────────────────────────────────────────
log "Step 5/10: Installing FFmpeg"
if ffmpeg -version &>/dev/null; then
    warn "FFmpeg already installed"
else
    apt-get install -y -q ffmpeg
    ok "FFmpeg installed"
fi
ffmpeg -version | head -1

# ── 6. Clone / update repository ────────────────────────────
log "Step 6/10: Cloning repository to $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    warn "Repo already exists — pulling latest"
    git -C "$APP_DIR" pull origin main || git -C "$APP_DIR" pull origin master
else
    git clone "$REPO_URL" "$APP_DIR"
    ok "Repository cloned"
fi

# ── 7. Backend: venv + dependencies ─────────────────────────
log "Step 7/10: Setting up Python backend"
cd "$APP_DIR/backend"

# Remove Windows FFmpeg binaries (not needed on Linux)
rm -f ffmpeg.exe ffprobe.exe ffplay.exe
ok "Removed Windows FFmpeg binaries"

# Create venv
python3.12 -m venv venv
source venv/bin/activate

pip install --upgrade pip wheel setuptools -q
ok "pip upgraded"

# Install requirements (heavy packages: torch, whisper — expect ~5-10 min)
warn "Installing Python dependencies (torch + whisper may take 5-10 min)..."
pip install -r requirements.txt
ok "Python dependencies installed"

deactivate

# ── 8. .env file validation ──────────────────────────────────
log "Step 8/10: Configuring backend .env"
if [ ! -f "$APP_DIR/backend/.env" ]; then
    echo "ERROR: .env file not found at $APP_DIR/backend/.env"
    echo "       Run the SCP command first (see README)."
    exit 1
fi

# Ensure SQLite is used (update DATABASE_URL if it's PostgreSQL)
if grep -q "^DATABASE_URL=postgresql" "$APP_DIR/backend/.env"; then
    warn "Switching DATABASE_URL from PostgreSQL to SQLite"
    sed -i 's|^DATABASE_URL=postgresql.*|DATABASE_URL=sqlite:///./clipsgold.db|' "$APP_DIR/backend/.env"
fi

# Ensure CORS allows frontend
if ! grep -q "$SERVER_IP:$FRONTEND_PORT" "$APP_DIR/backend/.env"; then
    warn "Adding server IP to CORS_ORIGINS"
    if grep -q "^CORS_ORIGINS=" "$APP_DIR/backend/.env"; then
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://${SERVER_IP}:${FRONTEND_PORT},http://localhost:${FRONTEND_PORT}|" "$APP_DIR/backend/.env"
    else
        echo "CORS_ORIGINS=http://${SERVER_IP}:${FRONTEND_PORT},http://localhost:${FRONTEND_PORT}" >> "$APP_DIR/backend/.env"
    fi
fi

# Ensure ENVIRONMENT=production
sed -i 's|^ENVIRONMENT=.*|ENVIRONMENT=production|' "$APP_DIR/backend/.env"
ok ".env configured"

# ── 9. Frontend: env + build ─────────────────────────────────
log "Step 9/10: Building Next.js frontend"
cd "$APP_DIR/frontend"

# Create .env.local with correct server URLs (baked into Next.js build)
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://${SERVER_IP}:${BACKEND_PORT}
NEXT_PUBLIC_WS_URL=ws://${SERVER_IP}:${BACKEND_PORT}
EOF
ok "frontend/.env.local created"

npm install --legacy-peer-deps
ok "npm install done"

npm run build
ok "Next.js build complete"

# ── 10. systemd services ─────────────────────────────────────
log "Step 10/10: Creating systemd services"

# Backend service
cat > /etc/systemd/system/clipsgold-backend.service << EOF
[Unit]
Description=ClipsGold Backend (FastAPI + Uvicorn)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR/backend
ExecStart=$APP_DIR/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --workers 1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
ok "clipsgold-backend.service created"

# Frontend service
cat > /etc/systemd/system/clipsgold-frontend.service << EOF
[Unit]
Description=ClipsGold Frontend (Next.js)
After=network.target clipsgold-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR/frontend
ExecStart=/usr/bin/node node_modules/.bin/next start -p $FRONTEND_PORT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF
ok "clipsgold-frontend.service created"

# Enable & start
systemctl daemon-reload
systemctl enable clipsgold-backend clipsgold-frontend
systemctl restart clipsgold-backend clipsgold-frontend
ok "Services enabled and started"

# ── Wait and verify ──────────────────────────────────────────
echo ""
log "Waiting 8s for services to start..."
sleep 8

echo ""
echo "═══════════════════════════════════════════"
echo "  SERVICE STATUS"
echo "═══════════════════════════════════════════"
systemctl is-active clipsgold-backend  && echo "  Backend:  RUNNING ✓" || echo "  Backend:  FAILED ✗"
systemctl is-active clipsgold-frontend && echo "  Frontend: RUNNING ✓" || echo "  Frontend: FAILED ✗"

echo ""
echo "  Checking HTTP endpoints..."
sleep 2
curl -s -o /dev/null -w "  Backend  http://${SERVER_IP}:${BACKEND_PORT}  → HTTP %{http_code}\n" \
    "http://localhost:${BACKEND_PORT}/" || echo "  Backend: no response yet"
curl -s -o /dev/null -w "  Frontend http://${SERVER_IP}:${FRONTEND_PORT} → HTTP %{http_code}\n" \
    "http://localhost:${FRONTEND_PORT}/" || echo "  Frontend: no response yet"

echo ""
echo "═══════════════════════════════════════════"
echo "  DEPLOY COMPLETE!"
echo ""
echo "  Frontend:  http://${SERVER_IP}:${FRONTEND_PORT}"
echo "  Backend:   http://${SERVER_IP}:${BACKEND_PORT}"
echo "  API docs:  http://${SERVER_IP}:${BACKEND_PORT}/docs"
echo ""
echo "  Logs:"
echo "    journalctl -u clipsgold-backend -f"
echo "    journalctl -u clipsgold-frontend -f"
echo "═══════════════════════════════════════════"
