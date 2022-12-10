FROM python:3.9.7
WORKDIR /app
COPY . /app
COPY ./src/main/params_docker.py /app/src/main/params.py
