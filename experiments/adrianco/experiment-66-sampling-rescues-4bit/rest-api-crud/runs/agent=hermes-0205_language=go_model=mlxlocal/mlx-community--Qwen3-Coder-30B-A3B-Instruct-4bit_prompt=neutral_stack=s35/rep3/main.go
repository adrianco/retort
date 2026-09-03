package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
)

// Book represents a book in our collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var db *sql.DB

func init() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}

	// Create tables if they don't exist
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
	 author TEXT NOT NULL,
	 year INTEGER,
	 isbn TEXT UNIQUE
	)`)

 if err != nil {
  log.Fatal("Failed to create table:", err)
 }
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func createBook(w http.ResponseWriter, r *http.Request) {
 var book Book
 if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 if book.Title == "" || book.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 // Insert into database
 result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
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

func getAllBooks(w http.ResponseWriter, r *http.Request) {
	// Check if author query parameter exists
 author := r.URL.Query().Get("author")
 var rows *sql.Rows
 var err error

 if author != "" {
 rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?", "%"+author+ "%")
 } else {
 rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
 }

 if err != nil {
 http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
 return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
 var b Book
 err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
 if err != nil {
 http.Error(w, "Failed to parse book data", http.StatusInternalServerError)
 return
 }
 books = append(books, b)
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(books)
}

func getBook(w http.ResponseWriter, r *http.Request) {
 id, err := strconv.Atoi(r.URL.Path[len("/books/"):])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
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

func updateBook(w http.ResponseWriter, r *http.Request) {
 id, err := strconv.Atoi(r.URL.Path[len("/books/"):])
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
 err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&book.ID)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 http.Error(w, "Failed to check book", http.StatusInternalServerError)
 return
 }

 // Update the book
 _, err = db.Exec("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?", book.Title, book.Author, book.Year, book.ISBN, id)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
 id, err := strconv.Atoi(r.URL.Path[len("/books/"):])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 _, err = db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 }

 w.WriteHeader(http.StatusNoContent)
}

func main() {
	// This is a minimal main function that just initializes the server
	// In a real implementation, this would run the HTTP server
}