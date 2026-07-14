
# Book API REST Service

## Setup
1. Install dependencies:
   ```
   pip install flask
   ```

2. Run the application:
   ```
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

## API Endpoints

- `POST /books` - Create a new book (requires JSON with title and author)
- `GET /books` - List all books (optional query parameter `?author=...`)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book (requires JSON with title and author)
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Testing

Run the tests with:
```
pytest test_app.py
```
