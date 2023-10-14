FROM python:3.10-alpine

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY . /usr/src/app

# Install packages neccessary to build
RUN apk add --update --no-cache build-base libffi-dev postgresql-dev zlib-dev jpeg-dev chromium chromium-chromedriver

# Install pip and Python dependencies
RUN pip install --upgrade pip &&\
    pip install -r requirements.txt

# Install npm and JS dependencies
#RUN apk add --update --no-cache nodejs npm &&\
    #npm install --save &&\
    #npm run build

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]