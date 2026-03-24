FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WP_HUNTER_HOST=0.0.0.0 \
    WP_HUNTER_PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY . .

RUN mkdir -p /licenses && \
    cp /app/LICENSE /licenses/WP-Hunter-MIT.txt && \
    cp /app/THIRD_PARTY_LICENSES.md /licenses/THIRD_PARTY_LICENSES.md && \
    cp /app/licenses/LGPL-2.1.txt /licenses/LGPL-2.1.txt && \
    cp /app/licenses/SEMGREP_SOURCE_NOTICE.txt /licenses/SEMGREP_SOURCE_NOTICE.txt

RUN useradd -m -u 10001 appuser && \
    mkdir -p /app/Plugins /app/semgrep_results /app/sessions && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["python", "wp-hunter.py"]
