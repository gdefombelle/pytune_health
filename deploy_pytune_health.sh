#!/bin/bash
set -e

# === CONFIG ===
REMOTE_SERVER="gabriel@195.201.9.184"
DATE_TAG="$(date +'%Y%m%d-%H%M%S')"
IMAGE_NAME="gdefombelle/pytune_health:${DATE_TAG}"
IMAGE_LATEST="gdefombelle/pytune_health:latest"

echo "=============================================="
echo " 🚀 Building PyTune Health Monitor"
echo "=============================================="
echo "Image: ${IMAGE_NAME}"
echo ""

# === DOCKER BUILD & PUSH ===
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t "${IMAGE_NAME}" \
  -t "${IMAGE_LATEST}" \
  --push \
  .

echo ""
echo "=============================================="
echo " 🌍 Deploying on remote server..."
echo "=============================================="

REMOTE_COMMAND="
docker stop pytune_health || true && \
docker rm pytune_health || true && \
docker pull ${IMAGE_NAME} && \

docker run -d --name pytune_health \
  --network pytune_network \
  -p 8010:8010 \
  --env-file /home/gabriel/pytune.env \
  -e DOCKERIZED=1 \
  --restart always \
  ${IMAGE_NAME}

docker restart pytune-nginx
"

ssh "${REMOTE_SERVER}" "${REMOTE_COMMAND}"

echo ""
echo "=============================================="
echo " ✅ Deployment complete!"
echo " 📦 Version deployed: ${DATE_TAG}"
echo "=============================================="