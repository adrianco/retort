FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Build deps for OApackage (orthogonal arrays — C++ extension, not always
# available as a wheel on every platform).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /tmp/build/
COPY src /tmp/build/src

RUN pip install --no-cache-dir /tmp/build[dev,test] \
    && rm -rf /tmp/build
