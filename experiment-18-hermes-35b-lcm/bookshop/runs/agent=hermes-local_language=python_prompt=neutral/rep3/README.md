# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- JSON responses with proper HTTP status codes

## Setup

1. Install dependencies:

```
pip install flask flask-sqlalchemy
```

2. Run the application:

```
python app.py
```

The API will be available at `http://localhost:5000`.

## API Endpoints

| Method   | Endpoint        | Description                     |
|----------|-----------------|---------------------------------|
| GET      | /health         | Health check                    |
| POST     | /books          | Create a new book               |
| GET      | /books          | List all books                  |
| GET      | /books?author=X | List books filtered by author   |
| GET      | /books/{id}     | Get a single book by ID         |
| PUT      | /books/{id}     | Update a book                   |
| DELETE   | /books/{id}     | Delete a book                   |

### POST /books - Create a new book

Request body (JSON):
```
{
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

- `title` and `author` are required.
- `year` and `isbn` are optional.

### GET /books - List all books

Returns a JSON array of all books. Supports filtering by author:

```
GET /books?author=Orwell
```

### GET /books/{id} - Get a book by ID

Returns a single book object.

### PUT /books/{id} - Update a book

Request body (JSON) - provide only the fields you want to update. All fields except `title` and `author` are optional.

### DELETE /books/{id} - Delete a book

Removes the book permanently.

## Testing

Run the test suite:

```
pytest test_app.py -v
```
