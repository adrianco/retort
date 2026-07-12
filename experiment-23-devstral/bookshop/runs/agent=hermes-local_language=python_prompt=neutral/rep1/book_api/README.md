# Book API REST Service

This is a REST API service for managing a book collection. It provides CRUD operations for books and includes a health check endpoint.

## Setup

1. Create a virtual environment:
   ```
   python3 -m venv venv
   ```

2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install flask
   ```

4. Run the application:
   ```
   python app.py
   ```

The API will be available at `http://localhost:5000`.

## API Endpoints

- **POST /books** - Create a new book
  - Request body: JSON with title, author, year (optional), and isbn (optional)
  - Example: `{"title": "To Kill a Mockingbird", "author": "Harper Lee", "year": 1960, "isbn": "9780061120084"}`

- **GET /books** - List all books
  - Query parameters:
    - `author` (optional): Filter books by author

- **GET /books/{id}** - Get a single book by ID

- **PUT /books/{id}** - Update a book
  - Request body: JSON with updated book information

- **DELETE /books/{id}** - Delete a book

- **GET /health** - Health check endpoint

## Testing

The application includes basic functionality tests. To run the tests:

1. Install pytest:
   ```
   pip install pytest
   ```

2. Run the tests:
   ```
   pytest test_app.py
   ```
