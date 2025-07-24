#!/bin/sh

python3 dashboard.py
cd /app && python3 -m http.server 8000 &

while true; do
  echo "Regenerating image..."
  python3 dashboard.py
  sleep 3600
done