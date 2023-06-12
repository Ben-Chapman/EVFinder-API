FROM python:3.10-slim

ENV API_HOME /api
WORKDIR $API_HOME

COPY requirements.txt .
COPY src $API_HOME/src

RUN pip3 install --no-cache-dir -r requirements.txt

CMD [ \
  "hypercorn", \
  "--worker-class", "uvloop", \
  "--workers", "2", \
  "--bind", ":8080", \
  "src.main:app" \
  ]
