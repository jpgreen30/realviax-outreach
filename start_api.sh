#!/bin/bash
# Stop any existing
pids=$(pgrep -f "uvicorn app.main:app" || true)
if [ -n "$pids" ]; then
  kill $pids 2>/dev/null || true
  sleep 1
fi
# Ensure port free
fuser -k 8000/tcp 2>/dev/null || true
sleep 1
# Start new
cd /home/jpgreen1/.openclaw/workspace/realviax-outreach
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > server_new.log 2>&1 &
echo $! > server_new.pid
sleep 2
echo "Server started:"
tail -5 server_new.log
