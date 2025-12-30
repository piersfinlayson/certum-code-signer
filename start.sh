set -e

echo "Building new Docker image..."
docker build -t code-signer .

echo "Killing existing container..."
docker rm -f code-signer || true

# To expose on a different port, for example 9443, modify the -p flag below to
# -p 9443:8443
echo "Starting new container..."
docker run -d \
  --name code-signer \
  --device=/dev/bus/usb \
  --privileged \
  -v /run/udev:/run/udev:ro \
  -p 0.0.0.0:8443:8443 \
  --env-file .env \
  code-signer
