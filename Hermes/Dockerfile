FROM python:3.6-slim-stretch
COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
RUN rm -f app.db
RUN python3 ./db_create.py
ENTRYPOINT ["python3"]
CMD ["run-production.py"]
