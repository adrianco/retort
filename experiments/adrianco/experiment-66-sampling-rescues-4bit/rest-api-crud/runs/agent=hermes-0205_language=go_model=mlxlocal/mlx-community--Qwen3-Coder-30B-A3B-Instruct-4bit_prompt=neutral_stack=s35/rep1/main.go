package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

// Book represents a book with its details
type Book struct {
	ID   int `json:"id"`
	Title string `json:"title"`
	Author string `json:"author"`
	Year int `json:"year"`
	ISBN string `json:"isbn"`
}

// Health response
type HealthResponse struct {
	Status string `json:"status"`
}

// BookRequest is used for creating/updating books
type BookRequest struct {
	Title string `json:"title"`
	Author string `json:"author"`
	Year int `json:"year"`
	ISBN string `json:"isbn"`
}

// Global database connection
var db *sql.DB

func main() {
	// Initialize database
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}
	defer db.Close()

	// Create tables if they don't exist
 createTables()

	// Create router and routes
	r := mux.NewRouter()
	r.HandleFunc("/health", healthCheck).Methods("GET")
	r.HandleFunc("/books", getBooks).Methods("GET")
	r.HandleFunc("/books", createBook).Methods("POST")
	r.HandleFunc("/books/{id}", getBook).Methods("GET")
	r.HandleFunc("/books/{id}", updateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")

	fmt.Println("Server starting on port 8080...")
	log.Fatal(http.ListenAndServe(":8080", r))
}

func createTables() {
	_, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
	 author TEXT NOT NULL,
	 year INTEGER,
	 isbn TEXT UNIQUE
	)`)

	if err != nil {
		log.Fatal("Failed to create tables:", err)
	}
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(HealthResponse{Status: "healthy"})
}

func getBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Get author filter from query parameters
 author := r.URL.Query().Get("author")
 
 var query string
 var rows *sql.Rows
 var err error

 if author != "" {
 query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
 rows, err = db.Query(query, author)
 } else {
 query = "SELECT id, title, author, year, isbn FROM books ORDER BY id"
 rows, err = db.Query(query)
 }

 if err != nil {
 http.Error(w, "Database query failed", http.StatusInternalServerError)
 return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
 var b Book
 err = rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
 if err != nil {
 http.Error(w, "Failed to scan book: "+err.Error(), http.StatusInternalServerError)
 return
 }
 books = append(books, b)
 }

 json.NewEncoder(w).Encode(books)
}

func getBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var b Book
 err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 } else {
 http.Error(w, "Database query failed: "+err.Error(), http.StatusInternalServerError)
 }
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(b)
}

func createBook(w http.ResponseWriter, r *http.Request) {
 var req BookRequest
 err := json.NewDecoder(r.Body).Decode(&req)
 if err != nil {
 http.Error(w, "Invalid JSON: "+err.Error(), http.StatusBadRequest)
 return
 }

 // Validate required fields
 if req.Title == "" {
 http.Error(w, "Title is required", http.StatusBadRequest)
 return
 }

 if req.Author == "" {
 http.Error(w, "Author is required", http.StatusBadRequest)
 return
 }

 // Insert new book
 res, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", req.Title, req.Author, req.Year, req.ISBN)
 if err != nil {
 http.Error(w, "Failed to create book: "+err.Error(), http.StatusInternalServerError)
 return
 }

 // Get the ID of the newly created book
 id, err := res.LastInsertId()
 if err != nil {
 http.Error(w, "Failed to get book ID: "+err.Error(), http.StatusInternalServerError)
 return
 }

 // Return the created book with ID
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(map[string]interface{}{
 "id": int(id),
 "title": req.Title,
 "author": req.Author,
 "year": req.Year,
 "isbn": req.ISBN,
 })
}

func updateBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var req BookRequest
 err = json.NewDecoder(r.Body).Decode(&req)
 if err != nil {
 http.Error(w, "Invalid JSON: "+err.Error(), http.StatusBadRequest)
 return
 }

 // Check if book exists
 var existingBook Book
 err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingBook.ID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 } else {
 http.Error(w, "Database query failed: "+err.Error(), http.StatusInternalServerError)
 }
 return
 }

 // Update the book
 _, err = db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", req.Title, req.Author, req.Year, req.ISBN, id)
 if err != nil {
 http.Error(w, "Failed to update book: "+err.Error(), http.StatusInternalServerError)
 return
 }

 // Return updated book
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]interface{}{
 "id": id,
 "title": req.Title,
 "author": req.Author,
 "year": req.Year,
 "isbn": req.ISBN,
 })
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
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
 http.Error(w, "Database query failed: "+err.Error(), http.StatusInternalServerError)
 }
 return
 }

 // Delete the book
 _, err = db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 http.Error(w, "Failed to delete book: "+err.Error(), http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}