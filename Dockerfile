# Muezza AI Dockerfile - Updated 2026-01-22
# Gunakan image Python yang ringan
FROM python:3.11-slim

# Cache bust
ARG CACHEBUST=1

# Set working directory di dalam container
WORKDIR /app

# Instal dependensi sistem yang diperlukan
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan instal
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode aplikasi Muezza AI
COPY . .

# Railway provides PORT env variable
ENV PORT=8501
EXPOSE $PORT

# Perintah untuk menjalankan Muezza AI Dashboard
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
