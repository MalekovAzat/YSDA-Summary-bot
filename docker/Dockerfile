FROM python:3.10-slim

ENV PYTHONPATH "${PYTHONPATH}:/app"

WORKDIR /app

COPY ./requirements.txt /app
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . .
