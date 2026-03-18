#!/bin/bash
# Start script — launches the backend and frontend.
# Assumes dependencies are already installed via setup.sh.

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Kill any existing instances
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

echo "=== Starting backend on port 8000 ==="
cd "$REPO_DIR/backend"
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/humanizer-backend.log 2>&1 &

echo "=== Starting frontend on port 3000 ==="
cd "$REPO_DIR/frontend"
nohup npm run dev -- -H 0.0.0.0 > /tmp/humanizer-frontend.log 2>&1 &

# Wait for services to come up
echo "=== Waiting for services ==="
for i in {1..15}; do
  backend=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null || echo "000")
  frontend=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
  if [ "$backend" = "200" ] && [ "$frontend" = "200" ]; then
    echo ""
    echo "=== App is running ==="
    echo "Backend:  http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    echo "Logs:     /tmp/humanizer-backend.log, /tmp/humanizer-frontend.log"
    exit 0
  fi
  printf "."
  sleep 2
done

echo ""
echo "Warning: services may still be starting. Check logs:"
echo "  tail -f /tmp/humanizer-backend.log"
echo "  tail -f /tmp/humanizer-frontend.log"
