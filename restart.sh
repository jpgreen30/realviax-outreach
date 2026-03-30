#!/bin/bash
# Restart Realviax Outreach backend
PID_FILE="/home/jpgreen1/.openclaw/workspace/realviax-outreach/server.pid"
if [ -f "$PID_FILE" ]; then
  kill $(cat "$PID_FILE") 2>/dev/null || true
  rm -f "$PID_FILE"
fi
# Ensure port 8000 is free
fuser -k 8000/tcp 2>/dev/null || true
sleep 1
cd /home/jpgreen1/.openclaw/workspace/realviax-outreach
nohup venv/bin/python run.py > server.log 2>&1 & echo $! > server.pid
sleep 2
echo "Server started, PID $(cat server.pid)"
tail -5 server.log
