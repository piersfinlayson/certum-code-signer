set -e

echo "Building new Docker image..."
docker build -t code-signer .

echo "Killing existing container..."
docker rm -f code-signer || true

# To expose on a different port, for example 9000, modify the -p flag below to
# -p 9000:8000
echo "Starting new container..."
docker run -d \
  --name code-signer \
  --device=/dev/bus/usb \
  --privileged \
  -v /run/udev:/run/udev:ro \
  -p 8000:8000 \
  --env-file .env \
  code-signer