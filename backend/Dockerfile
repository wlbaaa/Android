FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    android-tools-adb \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir websockify

WORKDIR /app

COPY server.py /app/server.py

EXPOSE 8080

CMD ["python3", "/app/server.py", "--port", "8080", "--host", "0.0.0.0"]
