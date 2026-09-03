package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in the collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Database connection
var db *sql.DB

// Initialize the database
func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	
	// Set connection parameters for better performance
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	
	// Create books table if it doesn't exist
	createTableQuery := `
CREATE TABLE IF NOT EXISTS books (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT NOT NULL,
	author TEXT NOT NULL,
	year INTEGER,
	isbn TEXT
);`
	
	_, err = db.Exec(createTableQuery)
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

// Create a new book
func createBookHandler(w http.ResponseWriter, r *http.Request) {
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

	// Insert into database
	query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
	result, err := db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
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

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// Get all books with optional author filter
func getBooksHandler(w http.ResponseWriter, r *http.Request) {
	var query string
	var args []interface{}

	// Check if author filter is provided
	author := r.URL.Query().Get("author")
	if author != "" {
		query = "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY id"
		args = append(args, "%"+author+"%")
	} else {
		query = "SELECT id, title, author, year, isbn FROM books ORDER BY id"
	}

	rows, err := db.Query(query, args...)
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

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

// Get a single book by ID
func getBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	var book Book
	query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
	err = db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
		}
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// Update a book
func updateBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
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
	query := "SELECT id FROM books WHERE id = ?"
	err = db.QueryRow(query, id).Scan(&existingBook.ID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
		}
		return
	}

	// Update the book
	updateQuery := "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
	_, err = db.Exec(updateQuery, book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		http.Error(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	// Return the updated book
	book.ID = id
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

// Delete a book
func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Check if book exists
	var existingBook Book
	query := "SELECT id FROM books WHERE id = ?"
	err = db.QueryRow(query, id).Scan(&existingBook.ID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
		}
		return
	}

	// Delete the book
	deleteQuery := "DELETE FROM books WHERE id = ?"
	_, err = db.Exec(deleteQuery, id)
	if err != nil {
		http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNoContent)
}

// Main function
func main() {
	initDB()

	// Create a new router
	r := mux.NewRouter()

	// Define routes
	r.HandleFunc("/health", healthHandler).Methods("GET")
	r.HandleFunc("/books", createBookHandler).Methods("POST")
	r.HandleFunc("/books", getBooksHandler).Methods("GET")
	r.HandleFunc("/books/{id}", getBookHandler).Methods("GET")
	r.HandleFunc("/books/{id}", updateBookHandler).Methods("PUT")
	r.HandleFunc("/books/{id}", deleteBookHandler).Methods("DELETE")

	// Start the server
	fmt.Println("Server starting on port 8080...")
	log.Fatal(http.ListenAndServe(":8080", r))
}