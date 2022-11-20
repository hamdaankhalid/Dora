FROM python:alpine3.10

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT FLASK_APP=/src/app.py flask run --host=0.0.0.0
