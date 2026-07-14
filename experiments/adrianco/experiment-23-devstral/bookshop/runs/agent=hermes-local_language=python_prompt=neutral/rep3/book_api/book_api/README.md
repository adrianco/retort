# Book API REST Service

## Setup and Run Instructions

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Run the application
```
python app.py
```

### 3. API Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `author` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

### 4. Example Requests

#### Create a book:
```
curl -X POST -H "Content-Type: application/json" -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "0451524934"}' http://localhost:5000/books
```

#### List books:
```
curl http://localhost:5000/books
```

#### List books by author:
```
curl "http://localhost:5000/books?author=George+Orwell"
```

#### Get a book by ID:
```
curl http://localhost:5000/books/1
```

#### Update a book:
```
curl -X PUT -H "Content-Type: application/json" -d '{"title": "Animal Farm", "author": "George Orwell", "year": 1945, "isbn": "0452284236"}' http://localhost:5000/books/1
```

#### Delete a book:
```
curl -X DELETE http://localhost:5000/books/1
```
