FROM python:3.12-slim

ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ram_miner /app/ram_miner
COPY data /app/data