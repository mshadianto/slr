#!/bin/bash
set -e

# Use PORT from environment or default to 8501
PORT="${PORT:-8501}"

echo "Starting Muezza AI on port $PORT..."
exec streamlit run app.py \
    --server.port="$PORT" \
    --server.address="0.0.0.0" \
    --server.headless=true \
    --server.fileWatcherType=none \
    --browser.gatherUsageStats=false
