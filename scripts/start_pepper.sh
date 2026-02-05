#!/bin/bash

# Configuration
PROJECT_ROOT=$(pwd)
OM1_ROOT="$(dirname "$PROJECT_ROOT")/OM1"
LOG_DIR="$PROJECT_ROOT/logs"

# Environment Variables
export HF_TOKEN="tu_token_aqui"
export REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Pepper System Unified Launcher ===${NC}"

# 1. Cleanup
echo -e "${YELLOW}Cleaning up old processes...${NC}"
pkill -9 -f "moshi.server" || true
pkill -9 -f "run.py pepper" || true
fuser -k 8998/tcp || true
fuser -k 8005/tcp || true

# 2. Setup Logs
mkdir -p "$LOG_DIR"
echo "" > "$LOG_DIR/moshi.log"
echo "" > "$LOG_DIR/om1.log"

# 3. Launch PersonaPlex (Moshi)
echo -e "${GREEN}Launching PersonaPlex (Moshi) on port 8998...${NC}"
SSL_DIR=$(mktemp -d)
PYTHONPATH=moshi ./venv/bin/python -m moshi.server \
    --ssl "$SSL_DIR" \
    --voice-prompt-dir ./voices \
    --static client/dist \
    --zenoh \
    --port 8998 > "$LOG_DIR/moshi.log" 2>&1 &

# 4. Launch OM1 (Pepper)
echo -e "${GREEN}Launching OM1 (Pepper) on port 8005...${NC}"
if [ -d "$OM1_ROOT" ]; then
    cd "$OM1_ROOT"
    . .venv/bin/activate
    python src/run.py pepper --log-level INFO > "$LOG_DIR/om1.log" 2>&1 &
    cd "$PROJECT_ROOT"
else
    echo -e "${RED}Error: OM1 directory not found at $OM1_ROOT${NC}"
    exit 1
fi

# 5. Health Check
echo -e "${YELLOW}Waiting for systems to initialize...${NC}"
sleep 5

echo -e "${BLUE}---------------------------------------${NC}"
echo -e "${GREEN}SYSTEMS LAUNCHED!${NC}"
echo -e "PersonaPlex UI: ${BLUE}https://localhost:8998${NC}"
echo -e "OM1 Simulator:  ${BLUE}http://localhost:8005${NC}"
echo -e ""
echo -e "Logs available at:"
echo -e "  - $LOG_DIR/moshi.log"
echo -e "  - $LOG_DIR/om1.log"
echo -e "${BLUE}---------------------------------------${NC}"
echo -e "Use 'tail -f logs/moshi.log' to monitor PersonaPlex"
echo -e "Use 'tail -f logs/om1.log' to monitor OM1"
echo -e "Use 'pkill -9 -f moshi' to stop the system"
