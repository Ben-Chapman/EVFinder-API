FROM python:3.10-slim

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY requirements.txt .
COPY ./src* $APP_HOME/

RUN pip3 install --no-cache-dir -r requirements.txt

# We're just copying the src directory into this container, so adjusting the imports
# to reflect this different directory layout
RUN sed -i 's/from src./from /g' *.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
