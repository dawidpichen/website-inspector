FROM python:3-slim

RUN mkdir /opt/website-inspector
WORKDIR /opt/website-inspector
COPY libs/ libs/
COPY *.py ./

RUN pip install kafka-python psycopg2_binary

CMD ["python", "./tests.py"]
