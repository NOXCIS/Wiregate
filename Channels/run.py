"""
Main module to run the Flask application with web sockets.
"""

from app import socket_io, app

def run() -> None:
    """Run the Flask app."""
    socket_io.run(app, host='0.0.0.0',port=80, debug=True)


if __name__ == '__main__':
    run()
