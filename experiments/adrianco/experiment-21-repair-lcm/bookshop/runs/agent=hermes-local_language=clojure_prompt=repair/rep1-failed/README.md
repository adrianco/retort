# Book API REST Service

A REST API service for managing a book collection, built with Clojure, Compojure, Ring, and SQLite.

## Prerequisites

- Java 11+ (OpenJDK works)
- Leiningen (Clojure build tool)

## Setup and Run

1. Install Leiningen if you haven't already:
   

2. Run the application:
   
   The server starts on port 3000 by default.

   To specify a different port:
   

## Running Tests



## API Endpoints

-  - Health check endpoint
-  - Create a new book
  - Body: 
  - Title and author are required
-  - List all books
  - Optional query param:  to filter by author
-  - Get a single book by ID
-  - Update a book (partial updates supported)
-  - Delete a book

## HTTP Status Codes

- 200 - Success
- 201 - Created (POST)
- 400 - Bad request (validation error or invalid ID)
- 404 - Not found
- 500 - Internal server error
