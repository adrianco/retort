package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in our collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Database connection
var db *sql.DB

// Initialize database
func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	// Create books table if it doesn't exist
	createTableSQL := `
CREATE TABLE IF NOT EXISTS books (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT NOT NULL,
	author TEXT NOT NULL,
	year INTEGER,
	isbn TEXT
);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		log.Fatal("Failed to create table:", err)
	}
}

// Health check endpoint
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// Get all books with optional author filter
func getBooksHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Parse query parameters
	query := r.URL.Query()
	author := query.Get("author")

	var rows *sql.Rows
	var err error

	if author != "" {
		// Filter by author
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?", "%"+author+"%")
	} else {
		// Get all books
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
	}

	if err != nil {
		http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			http.Error(w, "Failed to scan book", http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	json.NewEncoder(w).Encode(books)
}

// Get a single book by ID
func getBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Extract ID from URL path - /books/{id} format
	path := r.URL.Path[len("/books/"):]
	id, err := strconv.Atoi(path)
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	var book Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)

	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
		}
		return
	}

	json.NewEncoder(w).Encode(book)
}

// Create a new book
func createBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Only allow POST on /books endpoint for creating books
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	// Insert book into database
	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	// Get the ID of the newly created book
	id, err := result.LastInsertId()
	if err != nil {
		http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
		return
	}

	book.ID = int(id)
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// Update a book
func updateBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Extract ID from URL path - /books/{id} format
	path := r.URL.Path[len("/books/"):]
	id, err := strconv.Atoi(path)
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Only allow PUT on /books/{id} endpoint for updating books
	if r.Method != "PUT" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	// Check if book exists
	var existingBook Book
	err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingBook.ID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to check book", http.StatusInternalServerError)
		}
		return
	}

	// Update book in database
	_, err = db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		http.Error(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	book.ID = id
	json.NewEncoder(w).Encode(book)
}

// Delete a book
func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Extract ID from URL path - /books/{id} format
	path := r.URL.Path[len("/books/"):]
	id, err := strconv.Atoi(path)
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Only allow DELETE on /books/{id} endpoint for deleting books
	if r.Method != "DELETE" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Check if book exists
	var existingBook Book
	err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingBook.ID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to check book", http.StatusInternalServerError)
		}
		return
	}

	// Delete book from database
	_, err = db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// Main function
func main() {
	// Initialize database
	initDB()

	// Set up routes using standard http package with proper path handling
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		// Handle books endpoints with proper routing
		if r.URL.Path == "/books/" {
			// This is just /books with trailing slash, should be handled by the books handler
			if r.Method == "GET" {
				getBooksHandler(w, r)
			} else if r.Method == "POST" {
				createBookHandler(w, r)
			} else {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
			return
		}
		
		// Check if this is a books/{id} pattern
		if len(r.URL.Path) > len("/books/") {
			// This is /books/{id} pattern
			// Handle GET /books/{id}
			if r.Method == "GET" {
				// Reuse the getBookHandler function
				getBookHandler(w, r)
			} else if r.Method == "PUT" {
				// Reuse the updateBookHandler function
				updateBookHandler(w, r)
			} else if r.Method == "DELETE" {
				// Reuse the deleteBookHandler function
				deleteBookHandler(w, r)
			} else {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
		} else {
			// Invalid path for books
			http.Error(w, "Not found", http.StatusNotFound)
		}
	})

	// Handle /books endpoint (list all books and create)
	http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/books" {
			if r.Method == "GET" {
				getBooksHandler(w, r)
			} else if r.Method == "POST" {
				createBookHandler(w, r)
			} else {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
		} else {
			// This is for other paths that start with /books but don't match the pattern
			http.Error(w, "Not found", http.StatusNotFound)
		}
	})

	// Start server
	port := "8080"
	if envPort := os.Getenv("PORT"); envPort != "" {
		port = envPort
	}

	log.Printf("Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}