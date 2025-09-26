# This will:

# Create the network if missing.

# Start ArangoDB if not already running.

# Wait until ArangoDB is fully ready.

# Launch your tester container interactively with proper environment variables.

#!/bin/bash
set -e

# Configuration
NETWORK_NAME="app-net"
ARANGO_CONTAINER="arangodb"
ARANGO_ROOT_PASSWORD="my-secret-password"
TESTER_IMAGE="research-kg-app-embedding-tester:latest"
APP_DIR="$(pwd)"

# Create network if it doesn't exist
if ! docker network ls --format '{{.Name}}' | grep -w "$NETWORK_NAME" > /dev/null; then
    echo "Creating Docker network: $NETWORK_NAME"
    docker network create "$NETWORK_NAME"
else
    echo "Docker network $NETWORK_NAME already exists"
fi

# Run ArangoDB
if ! docker ps --format '{{.Names}}' | grep -w "$ARANGO_CONTAINER" > /dev/null; then
    echo "Starting ArangoDB container..."
    docker run -d \
        --name "$ARANGO_CONTAINER" \
        --network "$NETWORK_NAME" \
        -e ARANGO_ROOT_PASSWORD="$ARANGO_ROOT_PASSWORD" \
        -p 8529:8529 \
        arangodb/arangodb
else
    echo "ArangoDB container already running"
fi

echo "Waiting for ArangoDB to be ready..."
until docker exec "$ARANGO_CONTAINER" arangosh --server.endpoint tcp://127.0.0.1:8529 --server.username root --server.password "$ARANGO_ROOT_PASSWORD" --javascript.execute "require('@arangodb').db._version();" > /dev/null 2>&1; do
    sleep 2
done
echo -e "\nArangoDB is ready!"

# arangosh \
#   --server.endpoint tcp://127.0.0.1:8529 \
#   --server.username root \
#   --server.password "$ARANGO_ROOT_PASSWORD" \
#   --javascript.execute-string "require('@arangodb').db._version();"

# # Wait for ArangoDB to be ready
# echo "Waiting for ArangoDB to be ready..."
# until docker exec "$ARANGO_CONTAINER" curl -sSf http://localhost:8529/_api/version > /dev/null 2>&1; do
#     # echo -n "."
#     sleep 2
# done
# echo -e "\nArangoDB is ready!"

# Run tester container
echo "Starting tester container..."
docker run --rm \
    --network "$NETWORK_NAME" \
    -v "$APP_DIR":/app \
    -w /app \
    -e ARANGODB_HOST="http://$ARANGO_CONTAINER:8529" \
    -e ARANGODB_USERNAME="root" \
    -e ARANGODB_PASSWORD="$ARANGO_ROOT_PASSWORD" \
    -e ARANGODB_DATABASE="_system" \
    -it "$TESTER_IMAGE" /bin/bash
