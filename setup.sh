#!/bin/sh
# Cross-platform Knowledge Base Setup
# Works on: Linux, macOS, Windows (Git Bash/WSL)

echo "=== Starting Knowledge Base Setup ==="

# Check Docker availability
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker not found. Install Docker Desktop first."
  exit 1
fi

# Detect if sudo is needed (Linux)
DOCKER_CMD="docker"
if ! docker info >/dev/null 2>&1; then
  echo "Docker requires sudo on this system"
  DOCKER_CMD="sudo docker"
fi

echo "1/4 Starting Ollama container..."
$DOCKER_CMD compose up -d ollama

echo "2/4 Waiting for Ollama initialization (15 seconds)..."
sleep 15

echo "3/4 Downloading nomic-embed-text model..."
$DOCKER_CMD compose exec ollama ollama pull nomic-embed-text

echo "4/4 Starting MindsDB..."
$DOCKER_CMD compose up -d

echo "=== Setup Complete ==="
echo "Verify containers: $DOCKER_CMD compose ps"
echo "Access MindsDB at: http://localhost:47334"