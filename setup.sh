# muli os setup 
echo "=== Starting Knowledge Base Setup ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker not found. Install Docker Desktop first."
  exit 1
fi


DOCKER_CMD="docker"
if ! docker info >/dev/null 2>&1; then
  echo "Docker requires sudo on this system"
  DOCKER_CMD="sudo docker"
fi

echo "1/4 Starting Ollama container..."
$DOCKER_CMD compose up -d ollama

echo "2/4 Waiting for Ollama initialization (10 seconds)..."
sleep 10

echo "3/4 📦 Pulling lightweight embedding model: nomic-embed-text"
$DOCKER_CMD compose exec ollama ollama pull nomic-embed-text

echo "✅ Models available:"
$DOCKER_CMD compose exec ollama ollama list

echo "4/4 Start MindsDB...run " 
$DOCKER_CMD compose up

echo "=== Setup Complete ==="
echo "Verify containers: $DOCKER_CMD compose ps"
echo "Access MindsDB at: http://localhost:47334"

