FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libc6 \
    libnss3 \
    dnsutils \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install -r requirements.txt

COPY . /app/

RUN chmod +x /app/start.sh

# Render sets the $PORT environment variable dynamically
EXPOSE 8000

CMD ["/app/start.sh"]