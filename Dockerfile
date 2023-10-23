FROM python:3.10-slim

ENV API_HOME /api
WORKDIR $API_HOME

COPY requirements.txt .
COPY src $API_HOME/src

RUN pip3 install --no-cache-dir -r requirements.txt

CMD [ \
  "uvicorn", \
  "src.main:app", \
  "--host", "0.0.0.0", \
  "--port", "8080", \
  "--loop", "uvloop", \
  "--http", "httptools", \
  "--ws", "none", \
  "--timeout-keep-alive", "30" \
  ]
