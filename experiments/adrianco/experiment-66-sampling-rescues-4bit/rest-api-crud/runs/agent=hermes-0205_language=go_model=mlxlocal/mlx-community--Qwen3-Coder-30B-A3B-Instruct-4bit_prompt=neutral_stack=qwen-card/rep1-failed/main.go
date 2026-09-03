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

type Book struct {
	ID    int64  `json:"id"`
	Title string `json:"title"`
	Author string `json:"author"`
 Year int `json:"year"`
 ISBN string `json:"isbn"`
}

type BookRequest struct {
	Title string `json:"title"`
	Author string `json:"author"`
 Year int `json:"year"`
 ISBN string `json:"isbn"`
}

type HealthResponse struct {
	Status string `json:"status"`
}

var db *sql.DB

func main() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to open database:", err)
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

 http.HandleFunc("GET /health", healthHandler)
 http.HandleFunc("GET /books", getBooksHandler)
 http.HandleFunc("GET /books/{id}", getBookHandler)
 http.HandleFunc("POST /books", createBookHandler)
 http.HandleFunc("PUT /books/{id}", updateBookHandler)
 http.HandleFunc("DELETE /books/{id}", deleteBookHandler)

 fmt.Println("Server starting on port 8080...")
 log.Fatal(http.ListenAndServe(":8080", nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(HealthResponse{Status: "OK"})
}

func getBooksHandler(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 
 // Get query parameters
 author := r.URL.Query().Get("author")
 yearStr := r.URL.Query().Get("year")
 year, err := strconv.Atoi(yearStr)
 if err != nil {
 year = 0
 }

 var query string
 var args []interface{}
 if author != "" {
 query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
 args = append(args, author)
 } else {
 query = "SELECT id, title, author, year, isbn FROM books"
 }

 // Add year filter if provided
 if year > 0 {
 query += " AND year = ?"
 args = append(args, year)
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

 json.NewEncoder(w).Encode(books)
}

func getBookHandler(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 || parts[2] == "" {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 id, err := strconv.ParseInt(parts[2], 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
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

func createBookHandler(w http.ResponseWriter, r *http.Request) {
 var req BookRequest
 if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
 http.Error(w, "Invalid JSON request", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if req.Title == "" || req.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 // Insert new book
 stmt, err := db.Prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
 if err != nil {
 http.Error(w, "Failed to prepare statement", http.StatusInternalServerError)
 return
 }
 defer stmt.Close()

 res, err := stmt.Exec(req.Title, req.Author, req.Year, req.ISBN)
 if err != nil {
 http.Error(w, "Failed to create book", http.StatusInternalServerError)
 return
 }

 id, err := res.LastInsertId()
 if err != nil {
 http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
 return
 }

 // Return created book with ID
 createdBook := Book{
 ID: id,
 Title: req.Title,
 Author: req.Author,
 Year: req.Year,
 ISBN: req.ISBN,
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(createdBook)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 || parts[2] == "" {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 id, err := strconv.ParseInt(parts[2], 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var req BookRequest
 if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
 http.Error(w, "Invalid JSON request", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if req.Title == "" || req.Author == "" {
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
 http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
 }
 return
 }

 // Update book
 stmt, err := db.Prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
 if err != nil {
 http.Error(w, "Failed to prepare statement", http.StatusInternalServerError)
 return
 }
 defer stmt.Close()

 _, err = stmt.Exec(req.Title, req.Author, req.Year, req.ISBN, id)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 return
 }

 // Return updated book
 updatedBook := Book{
 ID: id,
 Title: req.Title,
 Author: req.Author,
 Year: req.Year,
 ISBN: req.ISBN,
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(updatedBook)
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 || parts[2] == "" {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 id, err := strconv.ParseInt(parts[2], 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingBook Book
 err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingBook.ID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 } else {
 http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
 }
 return
 }

 // Delete the book
 _, err = db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"message": "Book deleted"})
}