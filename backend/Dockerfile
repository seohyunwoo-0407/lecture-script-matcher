FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /app/storage/jobs

ENV JOB_STORAGE_DIR=/app/storage/jobs
ENV WHISPER_MODEL=base
ENV WHISPER_DEVICE=cpu
ENV WHISPER_COMPUTE_TYPE=int8
ENV WHISPER_BEAM_SIZE=1
ENV WHISPER_CPU_THREADS=2
ENV LOW_MEMORY=1
ENV OPENAI_MAX_CONCURRENCY=2

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
