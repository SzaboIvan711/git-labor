# Multi-stage build: the builder stage installs dependencies, the runtime image
# carries neither pip cache nor compilers. Result: a smaller image and less
# attack surface.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM base AS runtime
# Never run containers as root: a process escape would otherwise be root inside
# the container, which is uncomfortably close to root on the host.
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser wsgi.py ./

USER appuser
EXPOSE 8000

ARG APP_VERSION=0.0.0-dev
ENV APP_VERSION=${APP_VERSION}

# One worker by default. The in-memory repository (used when DATABASE_URL is
# unset) is per-process, so a second worker would serve a second, different
# task list. Once DATABASE_URL points at Postgres the state is shared and you
# should raise this — docker-compose.yml sets GUNICORN_WORKERS=2.
ENV GUNICORN_WORKERS=1

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

# sh -c so ${GUNICORN_WORKERS} expands; exec so gunicorn becomes PID 1 and
# receives SIGTERM directly (graceful shutdown on `docker stop`).
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS} --access-logfile - wsgi:app"]
