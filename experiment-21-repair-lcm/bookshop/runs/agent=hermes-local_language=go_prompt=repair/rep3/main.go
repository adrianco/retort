package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

// Book represents a book in the collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookStore handles database operations
type BookStore struct {
	db *sql.DB
}

// NewBookStore creates a new BookStore with the given database path
func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Enable WAL mode for better concurrency
	if _, err := db.Exec("PRAGMA journal_mode=WAL"); err != nil {
		return nil, fmt.Errorf("failed to set journal mode: %w", err)
	}

	// Create books table if it doesn't exist
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`

	if _, err := db.Exec(createTableSQL); err != nil {
		return nil, fmt.Errorf("failed to create table: %w", err)
	}

	return &BookStore{db: db}, nil
}

// Close closes the database connection
func (s *BookStore) Close() error {
	return s.db.Close()
}

// CreateBook creates a new book and returns it with the generated ID
func (s *BookStore) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	result, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		title, author, year, isbn,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("failed to get last insert ID: %w", err)
	}

	return &Book{
		ID:     int(id),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// GetBookByID retrieves a book by its ID
func (s *BookStore) GetBookByID(id int) (*Book, error) {
	var book Book
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}
	return &book, nil
}

// ListBooks retrieves all books, optionally filtered by author
func (s *BookStore) ListBooks(authorFilter string) ([]*Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		rows, err = s.db.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author = ?",
			authorFilter,
		)
	} else {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books")
	}
	if err != nil {
		return nil, fmt.Errorf("failed to list books: %w", err)
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, &book)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	if books == nil {
		books = make([]*Book, 0)
	}

	return books, nil
}

// UpdateBook updates an existing book
func (s *BookStore) UpdateBook(id int, title, author string, year int, isbn string) (*Book, error) {
	// Check if book exists
	existing, err := s.GetBookByID(id)
	if err != nil {
		return nil, fmt.Errorf("failed to check book existence: %w", err)
	}
	if existing == nil {
		return nil, nil
	}

	_, err = s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to update book: %w", err)
	}

	return &Book{
		ID:     id,
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// DeleteBook deletes a book by its ID
func (s *BookStore) DeleteBook(id int) error {
	_, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}
	return nil
}

// ServeHTTP handles HTTP requests for the book endpoints
func (bs *BookStore) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Parse the URL path to extract the book ID if present
	path := strings.TrimPrefix(r.URL.Path, "/books")
	path = strings.TrimPrefix(path, "/")

	switch {
	case r.Method == http.MethodPost && path == "":
		bs.createBook(w, r)
	case r.Method == http.MethodGet && path == "":
		bs.listBooks(w, r)
	case r.Method == http.MethodGet && path != "":
		bs.getBook(w, r, path)
	case r.Method == http.MethodPut && path != "":
		bs.updateBook(w, r, path)
	case r.Method == http.MethodDelete && path != "":
		bs.deleteBook(w, r, path)
	default:
		http.Error(w, `{"error":"Not found"}`, http.StatusNotFound)
	}
}

// validateBook validates required fields
func validateBook(book *Book) (string, int) {
	book.Title = strings.TrimSpace(book.Title)
	book.Author = strings.TrimSpace(book.Author)
	book.ISBN = strings.TrimSpace(book.ISBN)

	if book.Title == "" {
		return `title is required`, http.StatusBadRequest
	}
	if book.Author == "" {
		return `author is required`, http.StatusBadRequest
	}
	if book.Year == 0 {
		return `year is required`, http.StatusBadRequest
	}
	return "", 0
}

// writeJSON writes a JSON response with the given status code
func writeJSON(w http.ResponseWriter, data interface{}, statusCode int) {
	w.WriteHeader(statusCode)
	if data != nil {
		json.NewEncoder(w).Encode(data)
	}
}

// createBook handles POST /books
func (bs *BookStore) createBook(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		writeJSON(w, map[string]string{"error": "invalid JSON"}, http.StatusBadRequest)
		return
	}

	if errMsg, statusCode := validateBook(&book); errMsg != "" {
		writeJSON(w, map[string]string{"error": errMsg}, statusCode)
		return
	}

	created, err := bs.CreateBook(book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			writeJSON(w, map[string]string{"error": "book with this ISBN already exists"}, http.StatusConflict)
			return
		}
		writeJSON(w, map[string]string{"error": err.Error()}, http.StatusInternalServerError)
		return
	}

	writeJSON(w, created, http.StatusCreated)
}

// listBooks handles GET /books
func (bs *BookStore) listBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	books, err := bs.ListBooks(authorFilter)
	if err != nil {
		writeJSON(w, map[string]string{"error": err.Error()}, http.StatusInternalServerError)
		return
	}

	writeJSON(w, books, http.StatusOK)
}

// getBook handles GET /books/{id}
func (bs *BookStore) getBook(w http.ResponseWriter, r *http.Request, path string) {
	id, err := strconv.Atoi(path)
	if err != nil {
		writeJSON(w, map[string]string{"error": "invalid book ID"}, http.StatusBadRequest)
		return
	}

	book, err := bs.GetBookByID(id)
	if err != nil {
		writeJSON(w, map[string]string{"error": err.Error()}, http.StatusInternalServerError)
		return
	}

	if book == nil {
		writeJSON(w, map[string]string{"error": "book not found"}, http.StatusNotFound)
		return
	}

	writeJSON(w, book, http.StatusOK)
}

// updateBook handles PUT /books/{id}
func (bs *BookStore) updateBook(w http.ResponseWriter, r *http.Request, path string) {
	id, err := strconv.Atoi(path)
	if err != nil {
		writeJSON(w, map[string]string{"error": "invalid book ID"}, http.StatusBadRequest)
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		writeJSON(w, map[string]string{"error": "invalid JSON"}, http.StatusBadRequest)
		return
	}

	// ID in URL takes precedence
	book.ID = id

	if errMsg, statusCode := validateBook(&book); errMsg != "" {
		writeJSON(w, map[string]string{"error": errMsg}, statusCode)
		return
	}

	updated, err := bs.UpdateBook(book.ID, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		writeJSON(w, map[string]string{"error": err.Error()}, http.StatusInternalServerError)
		return
	}

	if updated == nil {
		writeJSON(w, map[string]string{"error": "book not found"}, http.StatusNotFound)
		return
	}

	writeJSON(w, updated, http.StatusOK)
}

// deleteBook handles DELETE /books/{id}
func (bs *BookStore) deleteBook(w http.ResponseWriter, r *http.Request, path string) {
	id, err := strconv.Atoi(path)
	if err != nil {
		writeJSON(w, map[string]string{"error": "invalid book ID"}, http.StatusBadRequest)
		return
	}

	if err := bs.DeleteBook(id); err != nil {
		writeJSON(w, map[string]string{"error": err.Error()}, http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func main() {
	port := "8080"
	store, err := NewBookStore("books.db")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer store.Close()

	mux := http.NewServeMux()
	mux.Handle("/books", store)
	mux.HandleFunc("/books/", store.ServeHTTP)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		writeJSON(w, map[string]string{"status": "healthy"}, http.StatusOK)
	})

	addr := fmt.Sprintf(":%s", port)
	log.Printf("Book API server starting on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
