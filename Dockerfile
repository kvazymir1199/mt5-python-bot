FROM python:3.12-slim
WORKDIR /app
COPY . /app

RUN pip install /app/requirements.txt

CMD ["python","-m","source/main"]