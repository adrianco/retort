package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
)

// Book represents a book in the database
type Book struct {
	ID   int64  `json:"id"`
	Title string `json:"title"`
	Author string `json:"author"`
 Year int `json:"year"`
 ISBN string `json:"isbn"`
}

// BookRequest represents the request body for creating/updating a book
type BookRequest struct {
	Title string `json:"title"`
	Author string `json:"author"`
 Year int `json:"year"`
 ISBN string `json:"isbn"`
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status string `json:"status"`
}

var db *sql.DB

func main() {
	var err error
	// Open SQLite database
 db, err = sql.Open("sqlite3", "./books.db")
 if err != nil {
 log.Fatal("Failed to connect to database:", err)
 }
 defer db.Close()

 // Create tables if they don't exist
 _, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 year INTEGER,
 isbn TEXT UNIQUE
 )`)
 if err != nil {
 log.Fatal("Failed to create tables:", err)
 }

 // Create indexes
 _, err = db.Exec("CREATE INDEX IF NOT EXISTS idx_author ON books(author)")
 if err != nil {
 log.Fatal("Failed to create index:", err)
 }

 // Setup routes
 http.HandleFunc("/health", healthHandler)
 http.HandleFunc("/books", booksHandler)
 http.HandleFunc("/books/", bookHandler)

 port := os.Getenv("PORT")
 if port == "" {
 port = "8080"
 }

 log.Printf("Server starting on port %s", port)
 log.Fatal(http.ListenAndServe(":"+port, nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 return
 }

 response := HealthResponse{Status: "OK"}
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(response)
}

func booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
 case http.MethodGet:
 getBooks(w, r)
 case http.MethodPost:
 postBook(w, r)
 default:
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
}

func bookHandler(w http.ResponseWriter, r *http.Request) {
 // Extract book ID from URL path
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 {
 http.Error(w, "Invalid URL", http.StatusNotFound)
 return
 }

 idStr := parts[3]
 id, err := strconv.ParseInt(idStr, 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusNotFound)
 return
 }

 switch r.Method {
 case http.MethodGet:
 getBook(w, r, id)
 case http.MethodPut:
 putBook(w, r, id)
 case http.MethodDelete:
 deleteBook(w, id)
 default:
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
}

func getBooks(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")

 query := r.URL.Query()
 author := query.Get("author")

 queryStr := "SELECT id, title, author, year, isbn FROM books"
 args := []interface{}{}

 if author != "" {
 queryStr += " WHERE author LIKE ?"
 args = append(args, "%"+author+"%")
 }

 rows, err := db.Query(queryStr, args...)
 if err != nil {
 http.Error(w, "Failed to query books", http.StatusInternalServerError)
 return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
 var book Book
 err = rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 http.Error(w, "Failed to scan book", http.StatusInternalServerError)
 return
 }
 book.Year = book.Year
 books = append(books, book)
 }

 json.NewEncoder(w).Encode(books)
}

func getBook(w http.ResponseWriter, r *http.Request, id int64) {
 var book Book
 query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
 err := db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Failed to get book", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func postBook(w http.ResponseWriter, r *http.Request) {
 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if bookReq.Title == "" {
 http.Error(w, "Title is required", http.StatusBadRequest)
 return
 }

 if bookReq.Author == "" {
 http.Error(w, "Author is required", http.StatusBadRequest)
 return
 }

 // Insert into database
 query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
 result, err := db.Exec(query, bookReq.Title, bookReq.Author, bookReq.Year, bookReq.ISBN)
 if err != nil {
 if strings.Contains(err.Error(), "UNIQUE constraint failed") {
 http.Error(w, "Book with this ISBN already exists", http.StatusConflict)
 return
 }
 http.Error(w, "Failed to create book", http.StatusInternalServerError)
 return
 }

 id, err := result.LastInsertId()
 if err != nil {
 http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
 return
 }

 // Return created book
 createdBook := Book{
 ID: id,
 Title: bookReq.Title,
 Author: bookReq.Author,
 Year: bookReq.Year,
 ISBN: bookReq.ISBN,
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(createdBook)
}

func putBook(w http.ResponseWriter, r *http.Request, id int64) {
 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if bookReq.Title == "" {
 http.Error(w, "Title is required", http.StatusBadRequest)
 return
 }

 if bookReq.Author == "" {
 http.Error(w, "Author is required", http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingBook Book
 err := db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingBook.ID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Failed to check book", http.StatusInternalServerError)
 return
 }

 // Update book
 query := "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?"
 _, err = db.Exec(query, bookReq.Title, bookReq.Author, bookReq.Year, bookReq.ISBN, id)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 return
 }

 // Return updated book
 updatedBook := Book{
 ID: id,
 Title: bookReq.Title,
 Author: bookReq.Author,
 Year: bookReq.Year,
 ISBN: bookReq.ISBN,
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(updatedBook)
}

func deleteBook(w http.ResponseWriter, id int64) {
 // Check if book exists
 var existingBook Book
 err := db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingBook.ID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Failed to check book", http.StatusInternalServerError)
 return
 }

 // Delete the book
 _, err = db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}