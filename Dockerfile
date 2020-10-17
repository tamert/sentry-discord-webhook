FROM python:3.8

COPY requirements.txt /tmp

RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . /app
WORKDIR /app

CMD python app.py
