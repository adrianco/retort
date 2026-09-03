package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type HealthResponse struct {
	Status string `json:"status"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	// Create table if it doesn't exist
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

	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	// Check if book with same ISBN already exists
	var existingID int
	err := db.QueryRow("SELECT id FROM books WHERE isbn = ?", book.ISBN).Scan(&existingID)
	if err == nil && existingID != 0 {
		http.Error(w, "Book with this ISBN already exists", http.StatusConflict)
		return
	}

	// Insert new book
	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	id, _ := result.LastInsertId()
 book.ID = int(id)

 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(book)
}

func getBooks(w http.ResponseWriter, r *http.Request) {
	// Get query parameters
 author := r.URL.Query().Get("author")
 year := 0
 if r.URL.Query().Get("year") != "" {
 year, _ = strconv.Atoi(r.URL.Query().Get("year"))
 }

 // Build query with optional filters
 query := "SELECT id, title, author, year, isbn FROM books"
 args := []interface{}{}

 // Apply filters if provided
 if author != "" {
 query += " WHERE author = ?"
 args = append(args, author)
 }

 if year != 0 {
 query += " AND year = ?"
 args = append(args, year)
 }

 // Execute query
 rows, err := db.Query(query, args...)
 if err != nil {
 http.Error(w, "Failed to query books", http.StatusInternalServerError)
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

func getBook(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/):]

 bookID, err := strconv.Atoi(id)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", bookID).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func updateBook(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/):]

 bookID, err := strconv.Atoi(id)
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
 var existingID int
 err = db.QueryRow("SELECT id FROM books WHERE id = ?", bookID).Scan(&existingID)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 // Update book
 _, err = db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", book.Title, book.Author, book.Year, book.ISBN, bookID)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 return
 }

 book.ID = bookID
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/):]

 bookID, err := strconv.Atoi(id)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 _, err = db.Exec("DELETE FROM books WHERE id = ?", bookID)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
 health := HealthResponse{Status: "healthy"}
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(health)
}

func main() {
 initDB()
 defer db.Close()

 // Register routes
 http.HandleFunc("/health", healthCheck)
 http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
 if r.Method == http.MethodPost {
 createBook(w, r)
 } else if r.Method == http.MethodGet {
 getBooks(w, r)
 } else {
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
 })

 http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
 if r.Method == http.MethodGet {
 getBook(w, r)
 } else if r.Method == http.MethodPut {
 updateBook(w, r)
 } else if r.Method == http.MethodDelete {
 deleteBook(w, r)
 } else {
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
 })

 port := ":8080"
 fmt.Printf("Server starting on port %s\n", port)
 log.Fatal(http.ListenAndServe(port, nil))
}