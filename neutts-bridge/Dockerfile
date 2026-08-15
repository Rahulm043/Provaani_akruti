FROM python:3.13-slim
RUN apt-get update && apt-get install -y build-essential python3-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV HF_HOME=/app/hf_cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from neutts import NeuTTS2E; tts = NeuTTS2E(); wav = tts.infer('Hello.', speaker='emily', emotion='neutral'); print(f'Pre-warmed: {len(wav)} samples')"
COPY main.py .
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV HF_HOME=/app/hf_cache
EXPOSE 8003
CMD ["python", "main.py"]
