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

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var db *sql.DB

func main() {
	// Initialize database
	initDB()
	defer closeDB()

	// Create router
	r := mux.NewRouter()

	// Define routes
	r.HandleFunc("/books", getBooks).Methods("GET")
	r.HandleFunc("/books/{id}", getBook).Methods("GET")
	r.HandleFunc("/books", createBook).Methods("POST")
	r.HandleFunc("/books/{id}", updateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")
	r.HandleFunc("/health", healthCheck).Methods("GET")

	// Start server
	fmt.Println("Starting server on :8080")
	log.Fatal(http.ListenAndServe(":8080", r))
}

func initDB() {
	// Open database connection
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}

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

func closeDB() {
	if db != nil {
		db.Close()
	}
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func getBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Get query parameters
	var query string
	params := r.URL.Query()
	author := params.Get("author")
	if author != "" {
		query = "SELECT * FROM books WHERE author LIKE ?"
	} else {
		query = "SELECT * FROM books"
	}

	// Execute query
	rows, err := db.Query(query, "%"+author+"%")
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	// Parse results
	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			http.Error(w, "Database scan error", http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	// Send response
	json.NewEncoder(w).Encode(books)
}

func getBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Get ID from URL
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	// Query database
	var book Book
	err = db.QueryRow("SELECT * FROM books WHERE id = ?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err.Error() == "sql: no rows in result set" {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Database error", http.StatusInternalServerError)
		}
		return
	}

	// Send response
	json.NewEncoder(w).Encode(book)
}

func createBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Parse request body
	var book Book
	err := json.NewDecoder(r.Body).Decode(&book)
	if err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	// Insert into database
	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Get the inserted ID
	id, err := result.LastInsertId()
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Fetch the newly created book
	var createdBook Book
	err = db.QueryRow("SELECT * FROM books WHERE id = ?", id).Scan(&createdBook.ID, &createdBook.Title, &createdBook.Author, &createdBook.Year, &createdBook.ISBN)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Send response
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(createdBook)
}

func updateBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Get ID from URL
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	// Parse request body
	var book Book
	err = json.NewDecoder(r.Body).Decode(&book)
	if err != nil {
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
	err = db.QueryRow("SELECT * FROM books WHERE id = ?", id).Scan(&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN)
	if err != nil {
		if err.Error() == "sql: no rows in result set" {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Database error", http.StatusInternalServerError)
		}
		return
	}

	// Update database
	_, err = db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Fetch the updated book
	var updatedBook Book
	err = db.QueryRow("SELECT * FROM books WHERE id = ?", id).Scan(&updatedBook.ID, &updatedBook.Title, &updatedBook.Author, &updatedBook.Year, &updatedBook.ISBN)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Send response
	json.NewEncoder(w).Encode(updatedBook)
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Get ID from URL
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	// Check if book exists
	var existingBook Book
	err = db.QueryRow("SELECT * FROM books WHERE id = ?", id).Scan(&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN)
	if err != nil {
		if err.Error() == "sql: no rows in result set" {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Database error", http.StatusInternalServerError)
		}
		return
	}

	// Delete from database
	_, err = db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Send success response
	w.WriteHeader(http.StatusNoContent)
}