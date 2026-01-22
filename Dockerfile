# Muezza AI Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT env variable (default 8501)
ENV PORT=8501

EXPOSE ${PORT}

# Run Streamlit (shell form to expand $PORT)
CMD sh -c "streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT} --server.headless=true --server.fileWatcherType=none"
