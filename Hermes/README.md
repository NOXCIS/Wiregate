[![Build status](https://travis-ci.org/juli1/flask-chat.svg?master)](https://travis-ci.org/juli1)
[![Coverage Status](https://coveralls.io/repos/github/juli1/flask-chat/badge.svg?branch=master)](https://coveralls.io/github/juli1/flask-chat?branch=master)

# Flask Chat
A simple chat in flask. More a message board that looks like
in the 80s than a full-featured chat with videos and unicorn.

Information about how to deploy using Docker on a raspberry pi on this 
[blog post](http://julien.gunnm.org/flask/python/docker/raspberry-pi/2017/12/03/developing-deploying-with-docker-on-raspberry-pi/).


## Why?
I wanted to have a simple chat with my friends and 
not use snapshot, hangouts or any other popular solutions
that requires to be logged on a system you do not control.

## What?
This is a simple application written in Python/Flask.
It handles a single chat window. Users have to authenticate.

## Requirements
* Single chat window
* Several users
* Admin functions to add/change users
* No plain password stored

### and for later ...
This could be integrated as well
* GIFs search
* Support to check HTML safety

## How to use it?
```bash
git clone https://github.com/juli1/flask-chat.git
cd flask-chat
# Replace the following line with virtualenv if necessary
python3.X -m venv venv # Replace X with your version of python
source venv/bin/activate
pip3 install -r requirements.txt
./db_create.py
./run-debug.py
```

And then, open your browser to [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

Start with the user *admin*, password *admin*.


## How to run tests?

```bash
python -m unittest discover tests
```

## Dockerization

The docker image is available on Docker Hub: [https://hub.docker.com/r/juli1/flask-chat/](https://hub.docker.com/r/juli1/flask-chat/)

Build the docker image
```bash
docker build -t flask-chat:latest .
```


Run the docker image
```bash
docker run -d -p 10000:5050 flask-chat
```


And then, open your browser to [http://127.0.0.1:10000/](http://127.0.0.1:10000/)


## Resources
* [The Flask Website](http://flask.pocoo.org/)
* [Dockerfile reference](https://docs.docker.com/engine/reference/builder/)
* [Docker container for Flask](http://containertutorials.com/docker-compose/flask-simple-app.html)
* [The Amazing Flask Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)
