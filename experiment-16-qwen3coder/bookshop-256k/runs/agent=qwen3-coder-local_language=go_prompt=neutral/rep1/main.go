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
	ISBN   string `json:"isbn"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, err
	}

	// Create books table
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return nil, err
	}

	return &BookStore{db: db}, nil
}

func (bs *BookStore) Close() error {
	return bs.db.Close()
}

func (bs *BookStore) CreateBook(book Book) (Book, error) {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id`
	err := bs.db.QueryRow(query, book.Title, book.Author, book.Year, book.ISBN).Scan(&book.ID)
	if err != nil {
		return book, err
	}
	return book, nil
}

func (bs *BookStore) GetBook(id int) (Book, error) {
	var book Book
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err := bs.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		return book, err
	}
	return book, nil
}

func (bs *BookStore) GetAllBooks(authorFilter string) ([]Book, error) {
	var books []Book
	var query string
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY title`
		rows, err = bs.db.Query(query, "%"+authorFilter+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books ORDER BY title`
		rows, err = bs.db.Query(query)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}

	return books, nil
}

func (bs *BookStore) UpdateBook(id int, book Book) (Book, error) {
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err := bs.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		return book, err
	}
	book.ID = id
	return book, nil
}

func (bs *BookStore) DeleteBook(id int) error {
	query := `DELETE FROM books WHERE id = ?`
	_, err := bs.db.Exec(query, id)
	return err
}

func (bs *BookStore) HealthCheck() error {
	return bs.db.Ping()
}

func writeJSON(w http.ResponseWriter, data interface{}, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func (bs *BookStore) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if err := bs.HealthCheck(); err != nil {
		writeJSON(w, map[string]string{"status": "error", "message": "Database connection failed"}, http.StatusInternalServerError)
		return
	}

	writeJSON(w, map[string]string{"status": "ok"}, http.StatusOK)
}

func (bs *BookStore) handleGetBooks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	author := r.URL.Query().Get("author")
	books, err := bs.GetAllBooks(author)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to retrieve books"}, http.StatusInternalServerError)
		return
	}

	writeJSON(w, books, http.StatusOK)
}

func (bs *BookStore) handleGetBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/books/"))
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	book, err := bs.GetBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to retrieve book", http.StatusInternalServerError)
		}
		return
	}

	writeJSON(w, book, http.StatusOK)
}

func (bs *BookStore) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validation
	if book.Title == "" {
		http.Error(w, "Title is required", http.StatusBadRequest)
		return
	}
	if book.Author == "" {
		http.Error(w, "Author is required", http.StatusBadRequest)
		return
	}

	createdBook, err := bs.CreateBook(book)
	if err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	writeJSON(w, createdBook, http.StatusCreated)
}

func (bs *BookStore) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/books/"))
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validation
	if book.Title == "" {
		http.Error(w, "Title is required", http.StatusBadRequest)
		return
	}
	if book.Author == "" {
		http.Error(w, "Author is required", http.StatusBadRequest)
		return
	}

	updatedBook, err := bs.UpdateBook(id, book)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to update book", http.StatusInternalServerError)
		}
		return
	}

	writeJSON(w, updatedBook, http.StatusOK)
}

func (bs *BookStore) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/books/"))
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	err = bs.DeleteBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		}
		return
	}

	writeJSON(w, map[string]string{"message": "Book deleted successfully"}, http.StatusOK)
}

func main() {
	// Initialize database
	dbPath := "./books.db"
	store, err := NewBookStore(dbPath)
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer store.Close()

	// Set up routes
	http.HandleFunc("/health", store.handleHealth)
	http.HandleFunc("/books", store.handleGetBooks)
	http.HandleFunc("/books/", store.handleGetBook)
	http.HandleFunc("/books", store.handleCreateBook)
	http.HandleFunc("/books/", store.handleUpdateBook)
	http.HandleFunc("/books/", store.handleDeleteBook)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Starting server on port %s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}