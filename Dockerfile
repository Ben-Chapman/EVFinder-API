FROM python:3.10-slim as builder
ENV PYTHONUNBUFFERED 1

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.10-alpine
WORKDIR /api
RUN apk -U add python3
COPY --from=builder /venv /venv

ENV PATH="/venv/bin:$PATH"
COPY src /api/src

CMD [ \
  "gunicorn", "src.main:app", \
  "--workers", "3", \
  "--timeout", "0", \
  "--worker-class", "uvicorn.workers.UvicornWorker", \
   "--bind", ":8080" \
   ]
