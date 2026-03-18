#!/bin/bash
# Setup script — run once on a fresh VM after cloning the repo.
# Installs all frontend and backend dependencies.

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing backend dependencies ==="
pip install -r "$REPO_DIR/backend/requirements.txt"

echo ""
echo "=== Installing frontend dependencies ==="
cd "$REPO_DIR/frontend"
npm install

echo ""
echo "=== Building frontend for production ==="
npm run build

echo ""
echo "=== Setup complete ==="
echo "All dependencies installed and frontend built. You can now run: bash start.sh"
