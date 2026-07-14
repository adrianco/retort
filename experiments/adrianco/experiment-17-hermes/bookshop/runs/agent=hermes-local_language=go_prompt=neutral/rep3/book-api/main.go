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

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	Isbn   string `json:"isbn"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal(err)
	}

	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER,
			isbn TEXT
		)
	`)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/books", booksHandler)
	http.HandleFunc("/books/", bookHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Server starting on port %s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case "GET":
		booksGetHandler(w, r)
	case "POST":
		booksPostHandler(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func bookHandler(w http.ResponseWriter, r *http.Request) {
	// Extract book ID from the URL
	path := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(path)
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	switch r.Method {
	case "GET":
		bookGetHandler(w, r, id)
	case "PUT":
		bookPutHandler(w, r, id)
	case "DELETE":
		bookDeleteHandler(w, r, id)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func booksGetHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	author := r.URL.Query().Get("author")
	
	var query string
	var args []interface{}
	
	if author != "" {
		query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
		args = []interface{}{author}
	} else {
		query = "SELECT id, title, author, year, isbn FROM books"
		args = []interface{}{}
	}

	rows, err := db.Query(query, args...)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
		if err != nil {
			http.Error(w, "Database scan error", http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	json.NewEncoder(w).Encode(books)
}

func booksPostHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

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

	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		book.Title, book.Author, book.Year, book.Isbn)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	book.ID = int(id)
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func bookGetHandler(w http.ResponseWriter, r *http.Request, id int) {
	w.Header().Set("Content-Type", "application/json")

	row := db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
	
	var book Book
	err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Database error", http.StatusInternalServerError)
		}
		return
	}

	json.NewEncoder(w).Encode(book)
}

func bookPutHandler(w http.ResponseWriter, r *http.Request, id int) {
	w.Header().Set("Content-Type", "application/json")

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

	// Check if book exists
	var existingBook Book
	row := db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
	err := row.Scan(&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.Isbn)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Database error", http.StatusInternalServerError)
		}
		return
	}

	_, err = db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", 
		book.Title, book.Author, book.Year, book.Isbn, id)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	book.ID = id
	json.NewEncoder(w).Encode(book)
}

func bookDeleteHandler(w http.ResponseWriter, r *http.Request, id int) {
	_, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
