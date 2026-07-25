# Book Collection REST API

This project provides a simple REST API for managing a collection of books. It is built with **FastAPI** and stores data in an **SQLite** database.

## Features

- Create, read, update, and delete books
- List all books with optional author filtering
- Health‑check endpoint
- Input validation (title and author required)
- SQLite persistence

## Setup

```bash
# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the API

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Running tests

```bash
pytest
```

All tests use an in‑memory SQLite database to avoid side effects.
