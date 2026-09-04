FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip & build tools
RUN pip install --no-cache-dir --upgrade pip wheel setuptools==77.0.3

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install OpenAI Whisper
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117

# Install spaCy English model
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Copy project files
COPY . .

# Ensure storage directories exist with write permissions
RUN mkdir -p uploads data && chmod -R 777 uploads data

# Set environment variables for Hugging Face Spaces
ENV HOST=0.0.0.0
ENV PORT=7860
ENV WHISPER_MODEL_SIZE=small
ENV PYTHONUNBUFFERED=1

# Expose default HF Spaces port
EXPOSE 7860

# Start FastAPI server
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
