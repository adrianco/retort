"""WSGI entrypoint for production servers (e.g. gunicorn, uWSGI).

Run with, for example::

    gunicorn wsgi:app
"""

from app import create_app

app = create_app()
