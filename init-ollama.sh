#!/bin/sh
docker compose up -d ollama
while ! docker compose exec ollama ollama pull nomic-embed-text; do
  sleep 5
done
docker compose up -d 