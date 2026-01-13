FROM python:3.14-slim

ENV API_HOME=/api
WORKDIR $API_HOME

COPY pyproject.toml uv.lock ./
COPY src ./src

# https://docs.astral.sh/uv/guides/integration/docker/#optimizations
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
  # Install non-dev packages
  uv sync --no-group dev

ENTRYPOINT [ \
  ".venv/bin/uvicorn", \
  "src.main:app", \
  "--host", "0.0.0.0", \
  "--port", "8080", \
  "--loop", "uvloop", \
  "--http", "httptools", \
  "--ws", "none", \
  "--timeout-keep-alive", "30" \
  ]
