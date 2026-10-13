# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
RUN useradd --create-home --uid 10001 raaz
COPY requirements.txt requirements-ml.txt ./
RUN pip install -r requirements.txt
# CPU-only PyTorch for the deep-learning clue classifier (set INSTALL_ML=0 to skip; the game still runs)
ARG INSTALL_ML=1
RUN if [ "$INSTALL_ML" = "1" ]; then pip install torch --index-url https://download.pytorch.org/whl/cpu; fi
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN mkdir -p /srv/artifacts && chown -R raaz:raaz /srv
USER raaz
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)"
# Migrations run on boot; `--timeout-graceful-shutdown` lets in-flight requests and background jobs finish.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 20 --proxy-headers --forwarded-allow-ips '*'"]
