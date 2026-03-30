#!/bin/bash
PID_FILE="server_new.pid"
if [ -f "$PID_FILE" ]; then
  kill $(cat "$PID_FILE") 2>/dev/null || true
  rm -f "$PID_FILE"
fi
fuser -k 8000/tcp 2>/dev/null || true
sleep 1
cd /home/jpgreen1/.openclaw/workspace/realviax-outreach
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > server_new.log 2>&1 & echo $! > server_new.pid
sleep 2
echo "Server started, PID $(cat server_new.pid)"
tail -5 server_new.log
