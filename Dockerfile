FROM python:3.10-slim

ENV APP_HOME /api
WORKDIR $APP_HOME

COPY requirements.txt .
COPY src $APP_HOME/src

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["python3", "src/main.py"]
