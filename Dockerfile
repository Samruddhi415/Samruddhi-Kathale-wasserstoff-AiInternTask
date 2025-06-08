FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories if they don't exist
RUN mkdir -p data/uploads data/chroma_db

# Make startup script executable
RUN chmod +x start.sh

# Expose the port Streamlit will run on
EXPOSE 8000

# Run both FastAPI and Streamlit
CMD ["./start.sh"]
