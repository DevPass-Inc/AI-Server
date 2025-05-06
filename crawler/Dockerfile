FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    unzip \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY crawler/ ./crawler

WORKDIR /app/crawler

ENV PATH="/usr/lib/chromium:/usr/bin:${PATH}"
ENV CHROME_BIN="/usr/bin/chromium"
ENV CHROMEDRIVER="/usr/bin/chromedriver"