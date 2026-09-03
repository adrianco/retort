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

// Book represents a book in our collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
 Year int `json:"year"`
 ISBN   string `json:"isbn"`
}

var db *sql.DB

func main() {
 var err error
 db, err = sql.Open("sqlite3", "./books.db")
 if err != nil {
 log.Fatal("Failed to connect to database:", err)
 }
 defer db.Close()

 // Create the books table if it doesn't exist
 _, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 year INTEGER,
 isbn TEXT
 )`)

 if err != nil {
 log.Fatal("Failed to create table:", err)
 }

 mux := http.NewServeMux()
 mux.HandleFunc("GET /health", healthCheck)
 mux.HandleFunc("POST /books", createBook)
 mux.HandleFunc("GET /books", listBooks)
 mux.HandleFunc("GET /books/{id}", getBook)
 mux.HandleFunc("PUT /books/{id}", updateBook)
 mux.HandleFunc("DELETE /books/{id}", deleteBook)

 fmt.Println("Starting server on port 8080...")
 fmt.Println("Available endpoints:")
 fmt.Println("GET /health - Health check")
 fmt.Println("POST /books - Create new book")
 fmt.Println("GET /books - List all books")
 fmt.Println("GET /books/{id} - Get a single book")
 fmt.Println("PUT /books/{id} - Update a book")
 fmt.Println("DELETE /books/{id} - Delete a book")

 log.Fatal(http.ListenAndServe(":8080", mux))
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func createBook(w http.ResponseWriter, r *http.Request) {
 if r.Method != http.MethodPost {
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

 // Insert into database
 query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
 result, err := db.Exec(query, book.Title, book.Author, book.Year, book.Isbn)
 if err != nil {
 http.Error(w, "Database error", http.StatusInternalServerError)
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

func listBooks(w http.ResponseWriter, r *http.Request) {
 queryParams := r.URL.Query()
 author := queryParams.Get("author")

 var query string
 var rows *sql.Rows
 var err error

 if author != "" {
 query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
 rows, err = db.Query(query, author)
 } else {
 query = "SELECT id, title, author, year, isbn FROM books"
 rows, err = db.Query(query)
 }

 if err != nil {
 http.Error(w, "Database query failed", http.StatusInternalServerError)
 return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
 var book Book
 err = rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
 if err != nil {
 http.Error(w, "Failed to scan row", http.StatusInternalServerError)
 return
 }
 books = append(books, book)
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(books)
}

func getBook(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 {
 http.Error(w, "Invalid URL", http.StatusBadRequest)
 return
 }

 id, err := strconv.Atoi(parts[3])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
 err = db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Database error", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func updateBook(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 {
 http.Error(w, "Invalid URL", http.StatusBadRequest)
 return
 }

 id, err := strconv.Atoi(parts[3])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingBook Book
 query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
 err = db.QueryRow(query, id).Scan(&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.Isbn)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Database error", http.StatusInternalServerError)
 return
 }

 // Update the book
 updateQuery := "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?"
 _, err = db.Exec(updateQuery, book.Title, book.Author, book.Year, book.Isbn, id)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 return
 }

 book.ID = id
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 {
 http.Error(w, "Invalid URL", http.StatusBadRequest)
 return
 }

 id, err := strconv.Atoi(parts[3])
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
 http.Error(w, "Database error", http.StatusInternalServerError)
 return
 }

 // Delete the book
 deleteQuery := "DELETE FROM books WHERE id = ?"
 _, err = db.Exec(deleteQuery, id)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}