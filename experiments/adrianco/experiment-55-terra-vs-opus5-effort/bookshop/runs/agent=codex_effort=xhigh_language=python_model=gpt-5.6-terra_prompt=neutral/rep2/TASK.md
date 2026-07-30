Create a REST API service for managing a book collection.

Requirements:
- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book

Technical constraints:
- Use the specified language and framework
- Store data in SQLite (or language-equivalent embedded DB)
- Return JSON responses with appropriate HTTP status codes
- Include input validation (title and author are required)
- Include a health check endpoint: GET /health

Deliverables:
- Working source code in the workspace directory
- A README.md with setup and run instructions
- At least 3 unit/integration tests
