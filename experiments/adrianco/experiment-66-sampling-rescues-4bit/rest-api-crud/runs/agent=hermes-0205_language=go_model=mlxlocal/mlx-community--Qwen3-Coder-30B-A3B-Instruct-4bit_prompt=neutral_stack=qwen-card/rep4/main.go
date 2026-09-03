package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
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
	createTable()

	// Setup routes
	http.HandleFunc("GET /health", healthHandler)
	http.HandleFunc("GET /books", getBooksHandler)
	http.HandleFunc("GET /books/{id}", getBookHandler)
	http.HandleFunc("POST /books", createBookHandler)
	http.HandleFunc("PUT /books/{id}", updateBookHandler)
	http.HandleFunc("DELETE /books/{id}", deleteBookHandler)

	fmt.Println("Starting server on port 8080...")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func createTable() {
 query := `
 CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);`
 _, err := db.Exec(query)
 if err != nil {
    log.Fatal("Failed to create table:", err)
 }
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
 response := map[string]string{"status": "healthy"}
 json.NewEncoder(w).Encode(response)
}

func getBooksHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

 query := "SELECT id, title, author, year, isbn FROM books"
 args := []interface{}{}

 // Handle author filter
 author := r.URL.Query().Get("author")
 if author != "" {
    query += " WHERE author = ?"
    args = append(args, author)
 }

 rows, err := db.Query(query, args...)
 if err != nil {
    http.Error(w, err.Error(), http.StatusInternalServerError)
    return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
    var book Book
    err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    books = append(books, book)
 }

 json.NewEncoder(w).Encode(books)
}

func getBookHandler(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/):]
 bookID, err := strconv.Atoi(id)
 if err != nil {
    http.Error(w, "Invalid book ID", http.StatusBadRequest)
    return
 }

 var book Book
 query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
 err = db.QueryRow(query, bookID).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
    if err == sql.ErrNoRows {
        http.Error(w, "Book not found", http.StatusNotFound)
        return
    }
    http.Error(w, err.Error(), http.StatusInternalServerError)
    return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func createBookHandler(w http.ResponseWriter, r *http.Request) {
 var bookReq BookRequest
 err := json.NewDecoder(r.Body).Decode(&bookReq)
 if err != nil {
    http.Error(w, "Invalid JSON", http.StatusBadRequest)
    return
 }

 // Validate required fields
 if bookReq.Title == "" || bookReq.Author == "" {
    http.Error(w, "Title and author are required", http.StatusBadRequest)
    return
 }

 query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
 result, err := db.Exec(query, bookReq.Title, bookReq.Author, bookReq.Year, bookReq.ISBN)
 if err != nil {
    http.Error(w, err.Error(), http.StatusInternalServerError)
    return
 }

 id, err := result.LastInsertId()
 if err != nil {
    http.Error(w, err.Error(), http.StatusInternalServerError)
    return
 }

 // Return the created book with ID
 createdBook := Book{
    ID:     int(id),
    Title:  bookReq.Title,
    Author: bookReq.Author,
    Year:   bookReq.Year,
    ISBN:   bookReq.ISBN,
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(createdBook)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/):]
 bookID, err := strconv.Atoi(id)
 if err != nil {
    http.Error(w, "Invalid book ID", http.StatusBadRequest)
    return
 }

 var bookReq BookRequest
 err = json.NewDecoder(r.Body).Decode(&bookReq)
 if err != nil {
    http.Error(w, "Invalid JSON", http.StatusBadRequest)
    return
 }

 // Validate required fields
 if bookReq.Title == "" || bookReq.Author == "" {
    http.Error(w, "Title and author are required", http.StatusBadRequest)
    return
 }

 query := "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
 _, err = db.Exec(query, bookReq.Title, bookReq.Author, bookReq.Year, bookReq.ISBN, bookID)
 if err != nil {
    http.Error(w, err.Error(), http.StatusInternalServerError)
    return
 }

 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"message": "Book updated successfully"})
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/):]
 bookID, err := strconv.Atoi(id)
 if err != nil {
    http.Error(w, "Invalid book ID", http.StatusBadRequest)
    return
 }

 query := "DELETE FROM books WHERE id = ?"
 _, err = db.Exec(query, bookID)
 if err != nil {
    http.Error(w, err.Error(), http.StatusInternalServerError)
    return
 }

 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"message": "Book deleted successfully"})
}