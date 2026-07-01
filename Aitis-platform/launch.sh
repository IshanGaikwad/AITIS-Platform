#!/usr/bin/env bash
#
# AITIS Platform — local dev launcher (macOS / Linux)
# Mirrors LAUNCH.bat for Unix. Starts the FastAPI backend (port 8001) and the
# Next.js frontend (port 3000), wiring the frontend proxy to the backend.
#
# Usage:   ./launch.sh        (Ctrl-C stops both servers)
#
set -euo pipefail

BACKEND_PORT=8001
FRONTEND_PORT=3000

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend/apps/web"

echo ""
echo "  AITIS Platform — starting..."
echo "  Backend  : http://localhost:$BACKEND_PORT"
echo "  Frontend : http://localhost:$FRONTEND_PORT"
echo ""

# ── 1. Wire the frontend to the backend (same value the proxy reads) ──────────
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:$BACKEND_PORT" > "$FRONTEND_DIR/.env.local"
echo "[1/4] Frontend env set (NEXT_PUBLIC_API_URL=http://127.0.0.1:$BACKEND_PORT)"

# ── 2. Free the ports if something is already listening ───────────────────────
free_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [ -n "$pids" ]; then
      echo "      freeing port $port (killing: $pids)"
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}
free_port "$BACKEND_PORT"
free_port "$FRONTEND_PORT"

# ── 3. Pick a Python interpreter (prefer backend venv) ────────────────────────
if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PYTHON="$BACKEND_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  PYTHON="python"
fi

# ── 4. Clear stale Next.js build cache (prevents ChunkLoadError on restart) ────
rm -rf "$FRONTEND_DIR/.next" 2>/dev/null || true

# ── Start both servers; ensure both die when this script exits ────────────────
PIDS=()
cleanup() {
  echo ""
  echo "  Stopping AITIS..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

echo "[2/4] Starting backend on port $BACKEND_PORT..."
( cd "$BACKEND_DIR" && exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" ) &
PIDS+=($!)

echo "[3/4] Starting frontend on port $FRONTEND_PORT..."
( cd "$FRONTEND_DIR" && exec npm run dev ) &
PIDS+=($!)

echo "[4/4] Both servers launching."
echo ""
echo "  Open http://localhost:$FRONTEND_PORT  (API docs: http://localhost:$BACKEND_PORT/docs)"
echo "  Press Ctrl-C to stop both."
echo ""

# Try to open the browser (macOS: open, Linux: xdg-open) after a short delay.
( sleep 8; (command -v open >/dev/null 2>&1 && open "http://localhost:$FRONTEND_PORT") \
  || (command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:$FRONTEND_PORT") || true ) &

# Wait on the servers; if either exits, clean up the other.
wait -n 2>/dev/null || true
cleanup
