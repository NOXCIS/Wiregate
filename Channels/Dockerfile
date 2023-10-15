FROM node:lts-alpine3.18
#FROM alpine:3.18.4
#FROM python:3.10-alpine
RUN npm install -g npm@latest
WORKDIR /usr/src/app

# Install packages neccessary to build
RUN apk add --update --no-cache build-base libffi-dev postgresql-dev zlib-dev jpeg-dev chromium chromium-chromedriver && \
    apk add --no-cache python3 py3-pip python3-dev py3-virtualenv py3-semver gcc curl rustup

COPY . /usr/src/app
# Install pip and Python dependencies
RUN pip install --upgrade pip       
RUN python3 -m pip install -r requirements.txt 

# Install npm and JS dependencies
RUN npm install --save 
RUN npm run build
RUN chmod u+x /usr/src/app/entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]

WORKDIR /usr/src/app