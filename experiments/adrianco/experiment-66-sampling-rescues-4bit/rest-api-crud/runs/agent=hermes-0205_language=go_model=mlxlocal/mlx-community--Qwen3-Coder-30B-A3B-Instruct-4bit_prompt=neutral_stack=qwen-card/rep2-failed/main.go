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
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID      int64  `json:"id"`
	Title   string `json:"title"`
	Author  string `json:"author"`
	Year    int    `json:"year"`
	Isbn    string `json:"isbn"`
}

type BookRequest struct {
	Title string `json:"title"`
	Author string `json:"author"`
	Year int `json:"year"`
	Isbn string `json:"isbn"`
}

type HealthResponse struct {
	Status string `json:"status"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}

	// Create books table if it doesn't exist
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
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(HealthResponse{Status: "healthy"})
}

func getAllBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Get query parameters
 author := r.URL.Query().Get("author")
 query := "SELECT id, title, author, year, isbn FROM books"
 params := []interface{}{}

 if author != "" {
	 query += " WHERE author = ?"
	 params = append(params, author)
 }

 rows, err := db.Query(query, params...)
 if err != nil {
	 http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
	 return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
	 var book Book
	 err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
	 if err != nil {
		 http.Error(w, "Failed to parse book data", http.StatusInternalServerError)
		 return
	 }
	 books = append(books, book)
 }

 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(books)
}

func getBook(w http.ResponseWriter, r *http.Request) {
 id := extractIDFromPath(r.URL.Path)
 book := Book{}

 query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
 err := db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
 if err != nil {
 if err == sql.ErrNoRows {
	 http.Error(w, "Book not found", http.StatusNotFound)
 } else {
	 http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
 }
 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(book)
}

func createBook(w http.ResponseWriter, r *http.Request) {
 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if bookReq.Title == "" || bookReq.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 // Insert new book
 query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
 result, err := db.Exec(query, bookReq.Title, bookReq.Author, bookReq.Year, bookReq.Isbn)
 if err != nil {
 http.Error(w, "Failed to create book", http.StatusInternalServerError)
 return
 }

 id, err := result.LastInsertId()
 if err != nil {
 http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
 return
 }

 // Return the created book with its ID
 createdBook := Book{
 ID: id,
 Title: bookReq.Title,
 Author: bookReq.Author,
 Year: bookReq.Year,
 Isbn: bookReq.Isbn,
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(createdBook)
}

func updateBook(w http.ResponseWriter, r *http.Request) {
 id := extractIDFromPath(r.URL.Path)
 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if bookReq.Title == "" || bookReq.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingBook Book
 err := db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingBook.ID)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 // Update the book
 query := "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
 _, err = db.Exec(query, bookReq.Title, bookReq.Author, bookReq.Year, bookReq.Isbn, id)
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
 Isbn: bookReq.Isbn,
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(updatedBook)
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
 id := extractIDFromPath(r.URL.Path)

 _, err := db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}

func extractIDFromPath(path string) int64 {
 parts := strings.Split(path, "/")
 id, _ := strconv.ParseInt(parts[len(parts)-1], 10, 64)
 return id
}

func main() {
 initDB()
 defer db.Close()

 // Register routes
 http.HandleFunc("/health", healthHandler)
 http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
 switch r.Method {
 case http.MethodGet:
 getAllBooks(w, r)
 case http.MethodPost:
 createBook(w, r)
 default:
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
 })

 http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
 switch r.Method {
 case http.MethodGet:
 getBook(w, r)
 case http.MethodPut:
 updateBook(w, r)
 case http.MethodDelete:
 deleteBook(w, r)
 default:
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
 })

 fmt.Println("Starting server on :8080")
 log.Fatal(http.ListenAndServe(":8080", nil))
}