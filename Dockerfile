# Gunakan image Python yang ringan
FROM python:3.11-slim

# Set working directory di dalam container
WORKDIR /app

# Instal dependensi sistem yang diperlukan untuk R-bridge atau library C
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan instal
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode aplikasi Muezza AI
COPY . .

# Port default untuk Streamlit
EXPOSE 8501

# Perintah untuk menjalankan Muezza AI Dashboard
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
