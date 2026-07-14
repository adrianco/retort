package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

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

func main() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	defer db.Close()

	// Initialize database
	initDB()

	// Set up routes
	http.HandleFunc("POST /books", createBook)
	http.HandleFunc("GET /books", listBooks)
	http.HandleFunc("GET /books/{id}", getBook)
	http.HandleFunc("PUT /books/{id}", updateBook)
	http.HandleFunc("DELETE /books/{id}", deleteBook)
	http.HandleFunc("GET /health", healthCheck)

	// Start server
	fmt.Println("Starting server on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

// initDB initializes the database with the books table
func initDB() {
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	_, err := db.Exec(createTableSQL)
	if err != nil {
		log.Fatal("Failed to create table:", err)
	}
}

// healthCheck returns a simple health check
func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// createBook handles POST /books
func createBook(w http.ResponseWriter, r *http.Request) {
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
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

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

// listBooks handles GET /books with optional author filter
func listBooks(w http.ResponseWriter, r *http.Request) {
	query := "SELECT id, title, author, year, isbn FROM books"
	var args []interface{}

	author := r.URL.Query().Get("author")
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
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

// getBook handles GET /books/{id}
func getBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
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
			return
		}
		http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// updateBook handles PUT /books/{id}
func updateBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
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
			return
		}
		http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
		return
	}

	// Update book
	updateQuery := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err = db.Exec(updateQuery, book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		http.Error(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	// Return updated book
	book.ID = id
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// deleteBook handles DELETE /books/{id}
func deleteBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
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
			return
		}
		http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
		return
	}

	// Delete book
	deleteQuery := "DELETE FROM books WHERE id = ?"
	_, err = db.Exec(deleteQuery, id)
	if err != nil {
		http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
