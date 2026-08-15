#!/usr/bin/env bash
# Deploy Dograh stack to GCP Compute Engine
# Prerequisites: Google Cloud SDK (gcloud) installed, authenticated, free trial active

set -euo pipefail

# ─── Configuration ──────────────────────────────────────────────
PROJECT_ID="${1:-dograh-deployment}"      # GCP project ID
VM_NAME="${2:-dograh-vm}"                 # VM name
ZONE="${3:-us-central1-a}"                # GCP zone
MACHINE_TYPE="${4:-e2-standard-2}"        # 2vCPU, 8GB RAM (~$0.07/hr)
DISK_SIZE="${5:-30}"                      # GB

REPO_URL="https://github.com/Rahulm043/dograh_test.git"
ENV_FILE=".env"                           # local .env file to upload

# ─── Colors ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}═══ Dograh GCP Deployment ═══${NC}"

# ─── 1. Check prerequisites ─────────────────────────────────────
command -v gcloud >/dev/null 2>&1 || { echo -e "${RED}Error: gcloud CLI not found. Install from https://cloud.google.com/sdk/docs/install${NC}"; exit 1; }
echo -e "${GREEN}[✓] gcloud CLI found${NC}"

# ─── 2. Setup GCP project ───────────────────────────────────────
echo -e "\n${YELLOW}[1/8] Creating GCP project...${NC}"
gcloud projects create "$PROJECT_ID" --name="Dograh Deployment" --set-as-default 2>/dev/null || {
  echo -e "${YELLOW}Project $PROJECT_ID already exists, setting as default...${NC}"
  gcloud config set project "$PROJECT_ID"
}

echo -e "${YELLOW}[2/8] Enabling Compute Engine API...${NC}"
gcloud services enable compute.googleapis.com --project="$PROJECT_ID"

echo -e "${YELLOW}[3/8] Creating firewall rules...${NC}"
# Allow HTTP, HTTPS, and custom ports for Dograh
gcloud compute firewall-rules create dograh-allow-http \
  --project="$PROJECT_ID" \
  --allow tcp:80,tcp:443,tcp:3000,tcp:3010,tcp:3011,tcp:8000,tcp:9000 \
  --source-ranges=0.0.0.0/0 \
  --description="Allow Dograh web + API traffic" 2>/dev/null || echo -e "${YELLOW}  Firewall rule already exists${NC}"

# ─── 3. Create VM ────────────────────────────────────────────────
echo -e "${YELLOW}[4/8] Creating VM ($MACHINE_TYPE, ${DISK_SIZE}GB)...${NC}"
gcloud compute instances create "$VM_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --boot-disk-size="${DISK_SIZE}GB" \
  --boot-disk-type=pd-standard \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=dograh-http \
  --metadata=startup-script-url=https://raw.githubusercontent.com/Rahulm043/dograh_test/master/deploy/startup.sh \
  || { echo -e "${RED}Failed to create VM. Check quota at https://console.cloud.google.com/iam-admin/quotas?project=$PROJECT_ID${NC}"; exit 1; }

echo -e "${GREEN}[✓] VM created${NC}"

# ─── 4. Get external IP ──────────────────────────────────────────
echo -e "${YELLOW}[5/8] Getting VM external IP...${NC}"
sleep 30  # wait for VM to get IP
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo -e "${GREEN}  External IP: $EXTERNAL_IP${NC}"

# ─── 5. Upload .env file ─────────────────────────────────────────
echo -e "${YELLOW}[6/8] Uploading .env file...${NC}"
if [ -f "$ENV_FILE" ]; then
  gcloud compute scp "$ENV_FILE" "${VM_NAME}:~/dograh_test/.env" --zone="$ZONE" --tunnel-through-iap 2>/dev/null || {
    # Fallback: SSH directly
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="mkdir -p ~/dograh_test"
    gcloud compute scp "$ENV_FILE" "${VM_NAME}:~/dograh_test/.env" --zone="$ZONE"
  }
  echo -e "${GREEN}[✓] .env uploaded${NC}"
else
  echo -e "${YELLOW}  Warning: .env file not found at $ENV_FILE. You'll need to upload it manually.${NC}"
fi

# ─── 6. Wait for startup script ──────────────────────────────────
echo -e "\n${YELLOW}[7/8] Waiting for VM startup script to complete (creates Docker stack)...${NC}"
echo -e "  This runs: install Docker, clone repo, docker compose up -d"
echo -e "  Check progress: gcloud compute ssh $VM_NAME --zone=$ZONE -- 'journalctl -u google-startup-scripts --no-pager -n 50'"

# Wait and check status
for i in $(seq 1 12); do
  sleep 15
  STATUS=$(gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null || echo 'waiting'" 2>/dev/null || echo "waiting")
  CONTAINER_COUNT=$(echo "$STATUS" | grep -c "dograh" 2>/dev/null || echo 0)
  echo -e "  [$((i*15))s] Containers up: $CONTAINER_COUNT"
  if echo "$STATUS" | grep -q "dograh.*Healthy\|dograh.*Up"; then
    echo -e "${GREEN}[✓] Stack is running!${NC}"
    break
  fi
done

# ─── 7. Show access info ─────────────────────────────────────────
echo -e "\n${GREEN}═══ Deployment Complete ═══${NC}"
echo -e ""
echo -e "  Dograh Admin UI:  ${GREEN}http://$EXTERNAL_IP:3010${NC}"
echo -e "  Custom Dashboard: ${GREEN}http://$EXTERNAL_IP:3011${NC}"
echo -e "  API:              ${GREEN}http://$EXTERNAL_IP:8000${NC}"
echo -e ""
echo -e "  SSH in:     gcloud compute ssh $VM_NAME --zone=$ZONE"
echo -e "  Stop VM:    gcloud compute instances stop $VM_NAME --zone=$ZONE"
echo -e "  Start VM:   gcloud compute instances start $VM_NAME --zone=$ZONE"
echo -e "  Delete VM:  gcloud compute instances delete $VM_NAME --zone=$ZONE"
echo -e ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Set the Plivo answer_url to http://$EXTERNAL_IP:8000/api/v1/telephony/plivo-xml"
echo -e "  2. Login to Dograh Admin at http://$EXTERNAL_IP:3010"
echo -e "  3. Access custom dashboard at http://$EXTERNAL_IP:3011"
echo -e ""
echo -e "${RED}Remember to STOP or DELETE the VM when done to avoid charges!${NC}"
