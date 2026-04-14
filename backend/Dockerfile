FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright (Chromium) + asyncpg
# Install Chromium's actual runtime deps manually instead of using --with-deps,
# which tries to install ttf-ubuntu-font-family / ttf-unifont that don't exist in Debian Trixie.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    # Chromium runtime dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium binary only (deps already installed above)
RUN playwright install chromium

COPY . .

EXPOSE 8000
