# Book API Service

## Overview
This is a REST API service for managing a book collection with the following features:
- Create new books with title, author, year, and ISBN
- List all books or filter by author
- Get individual books by ID
- Update book details
- Delete books

## Requirements
- Python 3.x
- Flask
- SQLite (included in Python standard library)

## Setup
1. Clone or copy this project to your local machine
2. Install Flask: `pip install flask`
3. Install SQLite (part of Python standard library) 

## Running the Application
1. Run the application: `python app.py`
2. The API will be available at http://localhost:5000

## API Endpoints
### Health Check
GET /health
Response: {"status": "healthy}

### Create a Book
POST /books
Body: { "title": "Book Title", "author": "Author Name", "year": 2020, "isbn": "1234567890" }
Response: {"id": 1, "message": "Book created successfully}

### Get All Books
GET /books
Response: [{ "id": 1, "title": "Book Title", "author": "Author Name", "year": 2020, "isbn": "1234567890" }

### Get a Book by ID
GET /books/{id}
Response: { "id": 1, "title": "Book Title", "author": "Author Name", "year": 2020, "isbn": "1234567890" }

### Update a Book
PUT /books/{id}
Body: { "title": "Updated Title", "author": "Updated Author", "year": 2021, "isbn": "1234567890" }
Response: {"message": "Book updated successfully}

### Delete a Book
DELETE /books/{id}
Response: {"message": "Book deleted successfully}