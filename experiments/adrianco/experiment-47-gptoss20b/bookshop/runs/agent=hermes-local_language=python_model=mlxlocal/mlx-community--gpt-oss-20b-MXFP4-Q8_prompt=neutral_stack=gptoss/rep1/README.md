# Book Collection API

## Overview
This repository contains a small FastAPI application that exposes a REST API for managing a collection of books. The data is persisted in a local SQLite database.

## Features
- **CRUD** operations for books
  - `POST /books` – create a new book
  - `GET /books` – list all books (optional `?author=` filter)
  - `GET /books/{id}` – retrieve a single book
  - `PUT /books/{id}` – update a book
  - `DELETE /books/{id}` – delete a book
- **Health check**: `GET /health`
- Input validation (title and author required)
- JSON responses with appropriate HTTP status codes
- Unit tests using `pytest` and FastAPI's `TestClient`

## Setup
```bash
# Optional: create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the API
```bash
uvicorn app:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## Running tests
```bash
pytest
```

## Project structure
```
app.py          # FastAPI application
requirements.txt
tests/
    test_app.py # unit tests
```
