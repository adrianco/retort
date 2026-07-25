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
	"time"

	"github.com/gorilla/mux"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in the collection
type Book struct {
	ID     int       `json:"id"`
	Title  string    `json:"title"`
	Author string    `json:"author"`
	Year   int       `json:"year"`
	ISBN   string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
}

// BookInput represents the input for creating/updating a book
type BookInput struct {
	Title  string `json:"title" validate:"required"`
	Author string `json:"author" validate:"required"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error string `json:"error"`
}

// SuccessResponse represents a success response
type SuccessResponse struct {
	Message string `json:"message"`
}

// HealthResponse represents a health check response
type HealthResponse struct {
	Status    string    `json:"status"`
	Timestamp time.Time `json:"timestamp"`
}

// DB represents the database connection
type DB struct {
	*sql.DB
}

// NewDB creates a new database connection
func NewDB(dbPath string) (*DB, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, err
	}

	// Create tables if they don't exist
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return nil, err
	}

	return &DB{db}, nil
}

// Validate validates the book input
func (b *BookInput) Validate() error {
	if strings.TrimSpace(b.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

// Server represents the HTTP server
type Server struct {
	router *mux.Router
	db     *DB
}

// NewServer creates a new server instance
func NewServer(db *DB) *Server {
	s := &Server{
		router: mux.NewRouter(),
		db:     db,
	}
	s.setupRoutes()
	return s
}

// setupRoutes sets up all the routes
func (s *Server) setupRoutes() {
	s.router.HandleFunc("/health", s.healthHandler).Methods("GET")
	s.router.HandleFunc("/books", s.listBooksHandler).Methods("GET")
	s.router.HandleFunc("/books", s.createBookHandler).Methods("POST")
	s.router.HandleFunc("/books/{id}", s.getBookHandler).Methods("GET")
	s.router.HandleFunc("/books/{id}", s.updateBookHandler).Methods("PUT")
	s.router.HandleFunc("/books/{id}", s.deleteBookHandler).Methods("DELETE")
}

// healthHandler handles the health check endpoint
func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now(),
	})
}

// listBooksHandler handles listing books with optional author filter
func (s *Server) listBooksHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	author := r.URL.Query().Get("author")

	var books []Book
	var err error

	if author != "" {
		books, err = s.db.GetBooksByAuthor(author)
	} else {
		books, err = s.db.GetBooks()
	}

	if err != nil {
		http.Error(w, `{"error":"Failed to retrieve books"}`, http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(books)
}

// createBookHandler handles creating a new book
func (s *Server) createBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	var input BookInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, `{"error":"Invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if err := input.Validate(); err != nil {
		http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
		return
	}

	book, err := s.db.CreateBook(&input)
	if err != nil {
		http.Error(w, `{"error":"Failed to create book"}`, http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// getBookHandler handles getting a single book by ID
func (s *Server) getBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	vars := mux.Vars(r)
	id := vars["id"]

	bookID, err := strconv.Atoi(id)
	if err != nil {
		http.Error(w, `{"error":"Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := s.db.GetBook(bookID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, `{"error":"Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error":"Failed to retrieve book"}`, http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

// updateBookHandler handles updating a book
func (s *Server) updateBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	vars := mux.Vars(r)
	id := vars["id"]

	bookID, err := strconv.Atoi(id)
	if err != nil {
		http.Error(w, `{"error":"Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	var input BookInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, `{"error":"Invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if err := input.Validate(); err != nil {
		http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
		return
	}

	book, err := s.db.UpdateBook(bookID, &input)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, `{"error":"Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error":"Failed to update book"}`, http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

// deleteBookHandler handles deleting a book
func (s *Server) deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	vars := mux.Vars(r)
	id := vars["id"]

	bookID, err := strconv.Atoi(id)
	if err != nil {
		http.Error(w, `{"error":"Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	err = s.db.DeleteBook(bookID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, `{"error":"Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error":"Failed to delete book"}`, http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// Start starts the HTTP server
func (s *Server) Start(port string) error {
	addr := ":" + port
	log.Printf("Server starting on port %s", port)
	return http.ListenAndServe(addr, s.router)
}

func main() {
	dbPath := os.Getenv("BOOK_DB_PATH")
	if dbPath == "" {
		dbPath = "./books.db"
	}

	db, err := NewDB(dbPath)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	server := NewServer(db)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	if err := server.Start(port); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
