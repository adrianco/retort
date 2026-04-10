FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

COPY pyproject.toml README.md /tmp/build/
COPY src /tmp/build/src

RUN pip install --no-cache-dir /tmp/build[dev,test] \
    && rm -rf /tmp/build
