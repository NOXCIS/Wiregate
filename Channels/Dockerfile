FROM node:current-alpine

WORKDIR /usr/src/app

# Install packages neccessary to build
RUN apk update && \
    apk add --update --no-cache build-base libffi-dev postgresql-dev zlib-dev jpeg-dev   && \
    apk add --no-cache python3 py3-pip py3-pillow python3-dev py3-virtualenv py3-psycopg2  py3-flask-wtf && \
    npm install -g npm@latest

COPY . /usr/src/app
# Install pip and Python dependencies
RUN pip install --upgrade pip --no-cache-dir --break-system-packages && \      
    python3 -m pip install -r requirements.txt --no-cache-dir --break-system-packages && \
    npm install --save && \
    npm run build && \
    chmod u+x /usr/src/app/entrypoint.sh

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
#WORKDIR /usr/src/app