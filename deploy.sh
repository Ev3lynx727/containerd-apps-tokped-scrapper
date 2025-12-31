#!/bin/bash

# Deploy script for Tokopedia Scraper
# Usage: ./deploy.sh <repo_url> <volume_path>

REPO_URL=$1
VOLUME_PATH=${2:-"/app/shared_volume"}

if [ -z "$REPO_URL" ]; then
    echo "Error: Please provide repository URL as first argument"
    exit 1
fi

echo "Auto-configuring environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    sudo apt update
    sudo apt install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    echo "Docker installed. Please log out and back in for group changes to take effect, or run 'newgrp docker'"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Installing Docker Compose..."
    sudo apt install -y docker-compose
fi

echo "Cloning repository..."
git clone $REPO_URL tokped-scraper-deploy

cd tokped-scraper-deploy

echo "Creating shared volume folder..."
mkdir -p $VOLUME_PATH

echo "Building and running container..."
docker-compose up --build -d

echo "Deployment complete. Container is running."