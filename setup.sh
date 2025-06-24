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

echo "1/6 Starting Ollama container..."
$DOCKER_CMD compose up -d ollama

echo "2/6 Waiting for Ollama initialization (15 seconds)..."
sleep 15

echo "3/6 📦 Pulling lightweight embedding model: nomic-embed-text"
sudo docker compose exec ollama ollama pull nomic-embed-text

echo "4/6 📦 Pulling Phi-3 instruction model: phi3"
sudo docker compose exec ollama ollama pull phi3

echo "5/6 📦 Pulling Gemma 2B for agent support"
sudo docker compose exec ollama ollama pull gemma:2b

echo "✅ Models available:"
$DOCKER_CMD compose exec ollama ollama list

echo "=== Setup Complete ==="
echo "Verify containers: $DOCKER_CMD compose ps"
echo "Access MindsDB at: http://localhost:47334"

echo "6/6 Start MindsDB...run ` sudo docker compose up` manually to see logs realtime for development"
