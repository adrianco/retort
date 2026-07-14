package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in the collection.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ErrorResponse represents an error response.
type ErrorResponse struct {
	Error string `json:"error"`
}

// BookStore holds the database connection.
type BookStore struct {
	DB *sql.DB
}

// NewBookStore creates a new BookStore with the given database.
func NewBookStore(db *sql.DB) (*BookStore, error) {
	createTable := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`

	if _, err := db.Exec(createTable); err != nil {
		return nil, fmt.Errorf("failed to create table: %w", err)
	}

	return &BookStore{DB: db}, nil
}

// writeJSON writes a JSON response.
func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

// writeError writes a JSON error response.
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, ErrorResponse{Error: message})
}

// healthHandler returns the health status of the service.
func (bs *BookStore) healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	if err := bs.DB.Ping(); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database not available")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// createBookHandler creates a new book.
func (bs *BookStore) createBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var input struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	if strings.TrimSpace(input.Title) == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if strings.TrimSpace(input.Author) == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	result, err := bs.DB.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		input.Title, input.Author, input.Year, input.ISBN,
	)
	if err != nil {
		writeError(w, http.StatusConflict, "book with this ISBN already exists")
		return
	}

	id, _ := result.LastInsertId()
	book := Book{
		ID:     int(id),
		Title:  input.Title,
		Author: input.Author,
		Year:   input.Year,
		ISBN:   input.ISBN,
	}

	writeJSON(w, http.StatusCreated, book)
}

// listBooksHandler lists all books with optional author filter.
func (bs *BookStore) listBooksHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	query := "SELECT id, title, author, year, isbn FROM books"
	var args []interface{}

	if author := r.URL.Query().Get("author"); author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}

	rows, err := bs.DB.Query(query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to query books")
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "failed to scan book")
			return
		}
		books = append(books, b)
	}

	if books == nil {
		books = []Book{}
	}

	writeJSON(w, http.StatusOK, books)
}

// getBookHandler gets a single book by ID.
func (bs *BookStore) getBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	var b Book
	err = bs.DB.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to query book")
		return
	}

	writeJSON(w, http.StatusOK, b)
}

// updateBookHandler updates an existing book.
func (bs *BookStore) updateBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	var input struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	if strings.TrimSpace(input.Title) == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if strings.TrimSpace(input.Author) == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	result, err := bs.DB.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		input.Title, input.Author, input.Year, input.ISBN, id,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	var b Book
	bs.DB.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

	writeJSON(w, http.StatusOK, b)
}

// deleteBookHandler deletes a book by ID.
func (bs *BookStore) deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	result, err := bs.DB.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// booksRouter handles /books (list and create).
func (bs *BookStore) booksRouter(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		bs.listBooksHandler(w, r)
	case http.MethodPost:
		bs.createBookHandler(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// bookRouter handles /books/{id}.
func (bs *BookStore) bookRouter(w http.ResponseWriter, r *http.Request) {
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")

	if len(pathParts) < 2 {
		writeError(w, http.StatusBadRequest, "invalid path")
		return
	}

	switch r.Method {
	case http.MethodGet:
		bs.getBookHandler(w, r)
	case http.MethodPut:
		bs.updateBookHandler(w, r)
	case http.MethodDelete:
		bs.deleteBookHandler(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// SetupRoutes configures all HTTP routes.
func (bs *BookStore) SetupRoutes() {
	http.HandleFunc("/health", bs.healthHandler)
	http.HandleFunc("/books/", bs.bookRouter)
	http.HandleFunc("/books", bs.booksRouter)
}

func main() {
	db, err := sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}

	bs, err := NewBookStore(db)
	if err != nil {
		log.Fatalf("failed to initialize book store: %v", err)
	}
	defer db.Close()

	bs.SetupRoutes()

	port := ":8080"
	log.Printf("Book API server starting on %s", port)
	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
