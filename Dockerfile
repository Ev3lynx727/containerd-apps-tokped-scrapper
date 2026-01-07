FROM python:3.10-slim

WORKDIR /app/tokped-scraper

COPY requirements.txt .
# Install system dependencies for python-levenshtein compilation
RUN apt-get update && \
    apt-get install -y \
        build-essential \
        python3-dev \
        netcat-openbsd && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y build-essential python3-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . .

# Generate self-signed SSL certificate for development
RUN openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Expose HTTPS port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8443/health')" || exit 1

CMD ["python", "server_restx.py"]