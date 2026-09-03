package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// Book represents a book with its details
type Book struct {
	ID     int64 `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int32 `json:"year"`
	ISBN   string `json:"isbn"`
}

// Database connection
var db *sql.DB

// setupDatabase initializes the database and creates tables
func setupDatabase() {
	var err error
 db, err = sql.Open("sqlite3", "./books.db")
 if err != nil {
 log.Fatal("Failed to connect to database:", err)
 }
 defer db.Close()

 // Create books table if it doesn't exist
 _, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 year INTEGER,
 isbn TEXT UNIQUE
)`)

 if err != nil {
 log.Fatal("Failed to create books table:", err)
 }
}

// Health check endpoint
func healthHandler(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// Get all books with optional filtering by author
func getBooksHandler(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")

 // Get author query parameter
 author := r.URL.Query().Get("author")
 var query string
 var args []interface{}

 if author != "" {
 query = "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?"
 args = append(args, "%"+author+ "%")
 } else {
 query = "SELECT id, title, author, year, isbn FROM books"
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
 err = rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 http.Error(w, "Failed to parse book data", http.StatusInternalServerError)
 return
 }
 books = append(books, book)
 }

 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(books)
}

// Get a single book by ID
func getBookHandler(w http.ResponseWriter, r *http.Request) {
 vars := strings.Split(r.URL.Path, "/")
 if len(vars) < 3 {
 http.Error(w, "Invalid URL path", http.StatusBadRequest)
 return
 }

 id, err := strconv.ParseInt(vars[2], 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// Create a new book
func createBookHandler(w http.ResponseWriter, r *http.Request) {
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

 // Create the book in database
 res, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
 if err != nil {
 http.Error(w, "Failed to create book", http.StatusInternalServerError)
 return
 }

 id, err := res.LastInsertId()
 if err != nil {
 http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
 return
 }

 book.ID = id
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(book)
}

// Update a book by ID
func updateBookHandler(w http.ResponseWriter, r *http.Request) {
 vars := strings.Split(r.URL.Path, "/")
 if len(vars) < 3 {
 http.Error(w, "Invalid URL path", http.StatusBadRequest)
 return
 }

 id, err := strconv.ParseInt(vars[2], 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

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
 var existingID int64
 err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingID)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 // Update the book
 _, err = db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", book.Title, book.Author, book.Year, book.ISBN, id)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// Delete a book by ID
func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
 vars := strings.Split(r.URL.Path, "/")
 if len(vars) < 3 {
 http.Error(w, "Invalid URL path", http.StatusBadRequest)
 return
 }

 id, err := strconv.ParseInt(vars[2], 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingID int64
 err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingID)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 _, err = db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}

// Main function to start the server
func main() {
 setupDatabase()

 // Setup routes
 http.HandleFunc("/health", healthHandler)
 http.HandleFunc("/books", getBooksHandler)
 http.HandleFunc("/books/", getBookHandler)
 http.HandleFunc("/books", createBookHandler)
 http.HandleFunc("/books/", updateBookHandler)
 http.HandleFunc("/books/", deleteBookHandler)

 fmt.Println("Starting server on port 8080...")
 log.Fatal(http.ListenAndServe(":8080", nil))
}