package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
)

// Book represents a book with its details
type Book struct {
	ID   int64 `json:"id,omitempty"`
}

// BookRequest represents the request body for creating/updating a book
type BookRequest struct {
	Title string `json:"title,omitempty"`
	Author string `json:"author,omitempty"`
	Year int `json:"year,omitempty"`
	ISBN string `json:"isbn,omitempty"`
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status string `json:"status"`
}

// BookStore handles book operations
type BookStore struct {
	db *sql.DB
}

// NewBookStore creates a new BookStore instance
func NewBookStore(dbPath string) (*BookStore, error) {
 db, err := sql.Open("sqlite3", dbPath)
 if err != nil {
 return nil, err
 }

 // Create the books table if it doesn't exist
 _, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 year INTEGER,
 isbn TEXT
)`)

 if err != nil {
 return nil, err
 }

 return &BookStore{db: db}, nil
}

// HealthHandler handles health check requests
func (bs *BookStore) HealthHandler(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(HealthResponse{Status: "healthy"})
}

// CreateBookHandler handles creating new books
func (bs *BookStore) CreateBookHandler(w http.ResponseWriter, r *http.Request) {
 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 if bookReq.Title == "" || bookReq.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 // Insert the book into the database
 _, err := bs.db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
 bookReq.Title, bookReq.Author, bookReq.Year, bookReq.Isbn)
 if err != nil {
 http.Error(w, "Failed to create book", http.StatusInternalServerError)
 return
 }

 // Get the last inserted ID
 id, err := bs.db.LastInsertId()
 if err != nil {
 http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
 return
 }

 // Return the created book with ID
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(map[string]interface{}{
 "id": id,
 "title": bookReq.Title,
 "author": bookReq.Author,
 "year": bookReq.Year,
 "isbn": bookReq.Isbn,
 })
}

// GetBookHandler handles getting a single book by ID
func (bs *BookStore) GetBookHandler(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path[len("/books/):1]
 id, err := strconv.ParseInt(path, 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 err = bs.db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&book.ID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
 return
 }

 var bookResponse BookResponse
 err = bs.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&bookResponse.ID, &bookResponse.Title, &bookResponse.Author, &bookResponse.Year, &bookResponse.Isbn)
 if err != nil {
 http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(bookResponse)
}

// UpdateBookHandler handles updating a book by ID
func (bs *BookStore) UpdateBookHandler(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path[len("/books/):1]
 id, err := strconv.ParseInt(path, 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingID int64
 err = bs.db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
 return
 }

 // Update the book
 _, err = bs.db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", 
 bookReq.Title, bookReq.Author, bookReq.Year, bookReq.Isbn, id)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]interface{}{
 "id": id,
 "title": bookReq.Title,
 "author": bookReq.Author,
 "year": bookReq.Year,
 "isbn": bookReq.Isbn,
 })
}

// DeleteBookHandler handles deleting a book by ID
func (bs *BookStore) DeleteBookHandler(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path[len("/books/):1]
 id, err := strconv.ParseInt(path, 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingID int64
 err = bs.db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
 return
 }

 // Delete the book
 _, err = bs.db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"message": "Book deleted successfully"})
}

// GetBooksHandler handles listing all books with optional author filter
func (bs *BookStore) GetBooksHandler(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")

 author := r.URL.Query().Get("author")
 query := "SELECT id, title, author, year, isbn FROM books"
 var args []interface{}
 if author != "" {
 query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
 args = append(args, author)
 }

 rows, err := bs.db.Query(query, args...)
 if err != nil {
 http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
 return
 }
 defer rows.Close()

 var books []BookResponse
 for rows.Next() {
 var book BookResponse
 err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
 if err != nil {
 http.Error(w, "Failed to parse book data", http.StatusInternalServerError)
 return
 }
 books = append(books, book)
 }

 json.NewEncoder(w).Encode(books)
}

// BookResponse represents the response structure for a book
type BookResponse struct {
	ID   int64 `json:"id"`
	Title string `json:"title"`
 Author string `json:"author"`
 Year int `json:"year"`
 ISBN string `json:"isbn"`
}

// StartServer starts the HTTP server
func StartServer() {
 store, err := NewBookStore("books.db")
 if err != nil {
 log.Fatal("Failed to create database:", err)
 }

 mux := http.NewServeMux()

 mux.HandleFunc("/health", store.HealthHandler)
 mux.HandleFunc("/books", store.CreateBookHandler)
 mux.HandleFunc("/books/", store.GetBookHandler)
 mux.HandleFunc("/books/", store.UpdateBookHandler)
 mux.HandleFunc("/books/", store.DeleteBookHandler)

 log.Println("Server starting on port 8080")
 log.Fatal(http.ListenAndServe(":8080", mux))
}

func main() {
 StartServer()
}