# Book Collection REST API

This project implements a simple REST API for managing a book collection. It is built with **Flask** and **SQLAlchemy** and stores data in an SQLite database.

## Features

- Create a book: `POST /books` (title, author, year, isbn)
- List books: `GET /books` (optionally filter by author with `?author=`)
- Retrieve a single book: `GET /books/{id}`
- Update a book: `PUT /books/{id}`
- Delete a book: `DELETE /books/{id}`
- Health check: `GET /health`

## Requirements

- Python 3.8+ (tested with 3.11)
- Flask
- SQLAlchemy

## Setup

```bash
# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install dependencies
pip install flask sqlalchemy

# Run the service
python main.py
```

The API will be available at `http://0.0.0.0:8000`.

## Running Tests

The test suite uses Flask's built‑in test client.

```bash
# Ensure dependencies are installed as above
python -m pytest tests/test_api.py
```

All tests should pass.
