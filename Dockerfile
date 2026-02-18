FROM python:3.12-slim

ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrapy.cfg /app/scrapy.cfg
COPY ram_miner /app/ram_miner