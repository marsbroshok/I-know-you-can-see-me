FROM python:3.7-slim-stretch

RUN apt-get update && apt-get install -y git python3-dev gcc libglib2.0-0 libsm6 libxrender1 libfontconfig1\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade -r requirements.txt

COPY app app/

WORKDIR app/

RUN python server.py

CMD python server.py serve
#CMD exec uvicorn --host "0.0.0.0" --port $PORT server:app
#CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 -k uvicorn.workers.UvicornWorker server:app