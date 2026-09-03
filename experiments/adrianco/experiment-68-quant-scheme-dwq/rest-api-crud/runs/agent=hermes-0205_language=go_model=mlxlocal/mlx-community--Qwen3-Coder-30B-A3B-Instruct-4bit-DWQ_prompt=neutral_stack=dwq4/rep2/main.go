package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
	"github.com/gorilla/mux"
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

	// Create books table if it doesn't exist
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	)`)
	if err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func createBookHandler(w http.ResponseWriter, r *http.Request) {
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
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := db.Exec(query, book.Title, book.Author, book.Year, book.Isbn)
	if err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	// Get the ID of the newly created book
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

func getBooksHandler(w http.ResponseWriter, r *http.Request) {
	// Get query parameters
	var query string
	var args []interface{}

	author := r.URL.Query().Get("author")
	if author != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY id`
		args = append(args, "%"+author+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books ORDER BY id`
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
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn); err != nil {
			http.Error(w, "Failed to scan book", http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func getBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	var book Book
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err = db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
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

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
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

	// Check if book exists
	var existingBook Book
	query := `SELECT id FROM books WHERE id = ?`
	err = db.QueryRow(query, id).Scan(&existingBook.ID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
			return
		}
		http.Error(w, "Failed to check book", http.StatusInternalServerError)
		return
	}

	// Update book
	updateQuery := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err = db.Exec(updateQuery, book.Title, book.Author, book.Year, book.Isbn, id)
	if err != nil {
		http.Error(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	book.ID = id
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Check if book exists
	var existingBook Book
	query := `SELECT id FROM books WHERE id = ?`
	err = db.QueryRow(query, id).Scan(&existingBook.ID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
			return
		}
		http.Error(w, "Failed to check book", http.StatusInternalServerError)
		return
	}

	// Delete book
	deleteQuery := `DELETE FROM books WHERE id = ?`
	_, err = db.Exec(deleteQuery, id)
	if err != nil {
		http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"message": "Book deleted successfully"})
}

func main() {
	initDB()
	defer db.Close()

	r := mux.NewRouter()
	
	r.HandleFunc("/health", healthHandler).Methods("GET")
	r.HandleFunc("/books", createBookHandler).Methods("POST")
	r.HandleFunc("/books", getBooksHandler).Methods("GET")
	r.HandleFunc("/books/{id}", getBookHandler).Methods("GET")
	r.HandleFunc("/books/{id}", updateBookHandler).Methods("PUT")
	r.HandleFunc("/books/{id}", deleteBookHandler).Methods("DELETE")

	fmt.Println("Server starting on port 8080...")
	log.Fatal(http.ListenAndServe(":8080", r))
}