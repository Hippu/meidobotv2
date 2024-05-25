FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install libffi-dev libnacl-dev build-essential ffmpeg --yes && pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "meidobot.py"]