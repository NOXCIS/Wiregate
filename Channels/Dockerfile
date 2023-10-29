FROM node:18-alpine3.18

WORKDIR /usr/src/app

# Install packages neccessary to build
RUN apk add --update --no-cache build-base libffi-dev postgresql-dev zlib-dev jpeg-dev chromium chromium-chromedriver && \
    apk add --no-cache python3 py3-pip python3-dev py3-virtualenv  && \
    npm install -g npm@latest

COPY . /usr/src/app
# Install pip and Python dependencies
RUN pip install --upgrade pip && \      
    python3 -m pip install -r requirements.txt && \
    npm install --save && \
    npm run build && \
    chmod u+x /usr/src/app/entrypoint.sh

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
#WORKDIR /usr/src/app