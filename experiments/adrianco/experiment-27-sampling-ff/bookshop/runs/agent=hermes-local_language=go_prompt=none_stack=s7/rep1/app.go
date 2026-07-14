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

// Book represents a book in the collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookStore provides CRUD operations for books
type BookStore struct {
	db *sql.DB
}

// NewBookStore creates a new BookStore with the given database path
func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	store := &BookStore{db: db}
	if err := store.initializeDB(); err != nil {
		return nil, fmt.Errorf("failed to initialize database: %w", err)
	}

	return store, nil
}

// initializeDB creates the books table if it doesn't exist
func (s *BookStore) initializeDB() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`
	_, err := s.db.Exec(query)
	return err
}

// Close closes the database connection
func (s *BookStore) Close() error {
	return s.db.Close()
}

// CreateBook creates a new book and returns it with the assigned ID
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
		return nil, fmt.Errorf("failed to get last insert id: %w", err)
	}

	return &Book{
		ID:     int(id),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// GetBook retrieves a book by its ID
func (s *BookStore) GetBook(id int) (*Book, error) {
	var book Book
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book with id %d not found", id)
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}
	return &book, nil
}

// ListBooks retrieves all books, optionally filtered by author
func (s *BookStore) ListBooks(authorFilter string) ([]Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		rows, err = s.db.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author = ?", authorFilter,
		)
	} else {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books")
	}
	if err != nil {
		return nil, fmt.Errorf("failed to list books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, book)
	}
	return books, nil
}

// UpdateBook updates an existing book
func (s *BookStore) UpdateBook(id int, title, author string, year int, isbn string) (*Book, error) {
	// Check if book exists
	_, err := s.GetBook(id)
	if err != nil {
		return nil, err
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
	// Check if book exists
	_, err := s.GetBook(id)
	if err != nil {
		return err
	}

	_, err = s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}
	return nil
}

// Server holds the HTTP server configuration
type Server struct {
	store *BookStore
	port  string
}

// NewServer creates a new Server
func NewServer(store *BookStore, port string) *Server {
	return &Server{store: store, port: port}
}

// startServer initializes and starts the HTTP server
func (s *Server) startServer() {
	http.HandleFunc("/health", s.healthHandler)
	http.HandleFunc("/books", s.booksHandler)
	http.HandleFunc("/books/", s.bookByIDHandler)

	addr := ":" + s.port
	fmt.Printf("Server starting on port %s\n", s.port)
	log.Fatal(http.ListenAndServe(addr, nil))
}

// writeJSON writes a JSON response with the given status code
func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

// writeError writes a JSON error response
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

// healthHandler handles GET /health
func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// booksHandler handles GET and POST /books
func (s *Server) booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.listBooks(w, r)
	case http.MethodPost:
		s.createBook(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// bookByIDHandler handles GET, PUT, and DELETE /books/{id}
func (s *Server) bookByIDHandler(w http.ResponseWriter, r *http.Request) {
	// Extract ID from URL path
	idStr := r.URL.Path[len("/books/"):]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	switch r.Method {
	case http.MethodGet:
		s.getBook(w, r, id)
	case http.MethodPut:
		s.updateBook(w, r, id)
	case http.MethodDelete:
		s.deleteBook(w, r, id)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// createBook handles POST /books
func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	// Validate required fields
	if input.Title == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if input.Author == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	book, err := s.store.CreateBook(input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, book)
}

// listBooks handles GET /books
func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	books, err := s.store.ListBooks(authorFilter)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if books == nil {
		books = []Book{}
	}

	writeJSON(w, http.StatusOK, books)
}

// getBook handles GET /books/{id}
func (s *Server) getBook(w http.ResponseWriter, r *http.Request, id int) {
	book, err := s.store.GetBook(id)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// updateBook handles PUT /books/{id}
func (s *Server) updateBook(w http.ResponseWriter, r *http.Request, id int) {
	var input struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	// Validate required fields
	if input.Title == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if input.Author == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	book, err := s.store.UpdateBook(id, input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// deleteBook handles DELETE /books/{id}
func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request, id int) {
	err := s.store.DeleteBook(id)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func main() {
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	store, err := NewBookStore(dbPath)
	if err != nil {
		log.Fatalf("Failed to create book store: %v", err)
	}
	defer store.Close()

	server := NewServer(store, port)
	server.startServer()
}
