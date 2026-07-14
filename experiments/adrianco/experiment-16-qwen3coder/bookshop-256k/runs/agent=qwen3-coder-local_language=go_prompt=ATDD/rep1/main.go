package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
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

// BookRequest represents the request payload for creating/updating a book
type BookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookResponse represents the response payload for a book
type BookResponse struct {
	Book Book `json:"book"`
}

// BooksResponse represents the response payload for listing books
type BooksResponse struct {
	Books []Book `json:"books"`
}

// BookRepository handles database operations for books
type BookRepository struct {
	db *sql.DB
}

// NewBookRepository creates a new BookRepository
func NewBookRepository(db *sql.DB) *BookRepository {
	return &BookRepository{db: db}
}

// CreateBook inserts a new book into the database
func (r *BookRepository) CreateBook(book *Book) error {
	query := `
		INSERT INTO books (title, author, year, isbn) 
		VALUES (?, ?, ?, ?)`
	
	_, err := r.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return fmt.Errorf("failed to create book: %w", err)
	}
	
	return nil
}

// GetBook retrieves a book by ID
func (r *BookRepository) GetBook(id int) (*Book, error) {
	query := `
		SELECT id, title, author, year, isbn 
		FROM books 
		WHERE id = ?`
	
	book := &Book{}
	err := r.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book not found with id: %d", id)
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}
	
	return book, nil
}

// ListBooks retrieves all books, optionally filtered by author
func (r *BookRepository) ListBooks(author string) ([]Book, error) {
	var query string
	var args []interface{}
	
	if author != "" {
		query = `
			SELECT id, title, author, year, isbn 
			FROM books 
			WHERE author = ?`
		args = []interface{}{author}
	} else {
		query = `
			SELECT id, title, author, year, isbn 
			FROM books`
	}
	
	rows, err := r.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to list books: %w", err)
	}
	defer rows.Close()
	
	var books []Book
	for rows.Next() {
		book := Book{}
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, book)
	}
	
	return books, nil
}

// UpdateBook updates an existing book
func (r *BookRepository) UpdateBook(id int, book *Book) error {
	query := `
		UPDATE books 
		SET title = ?, author = ?, year = ?, isbn = ? 
		WHERE id = ?`
	
	result, err := r.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		return fmt.Errorf("failed to update book: %w", err)
	}
	
	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to get rows affected: %w", err)
	}
	
	if rowsAffected == 0 {
		return fmt.Errorf("book not found with id: %d", id)
	}
	
	return nil
}

// DeleteBook deletes a book by ID
func (r *BookRepository) DeleteBook(id int) error {
	query := `
		DELETE FROM books 
		WHERE id = ?`
	
	result, err := r.db.Exec(query, id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}
	
	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to get rows affected: %w", err)
	}
	
	if rowsAffected == 0 {
		return fmt.Errorf("book not found with id: %d", id)
	}
	
	return nil
}

// BookService handles the business logic for books
type BookService struct {
	repo *BookRepository
}

// NewBookService creates a new BookService
func NewBookService(repo *BookRepository) *BookService {
	return &BookService{repo: repo}
}

// CreateBookHandler handles creating a new book
func (s *BookService) CreateBookHandler(w http.ResponseWriter, r *http.Request) {
	var req BookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "Invalid JSON"}`, http.StatusBadRequest)
		return
	}

	// Validation
	if req.Title == "" {
		http.Error(w, `{"error": "Title is required"}`, http.StatusBadRequest)
		return
	}
	if req.Author == "" {
		http.Error(w, `{"error": "Author is required"}`, http.StatusBadRequest)
		return
	}

	// Create the book
	book := &Book{
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	err := s.repo.CreateBook(book)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE constraint failed") {
			http.Error(w, `{"error": "ISBN already exists"}`, http.StatusConflict)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	// Get the last inserted ID (SQLite auto-increment)
	var lastID int
	err = s.repo.db.QueryRow("SELECT last_insert_rowid()").Scan(&lastID)
	if err != nil {
		http.Error(w, fmt.Sprintf(`{"error": "Failed to get created book ID"}`), http.StatusInternalServerError)
		return
	}

	// Get the created book to return it
	createdBook, err := s.repo.GetBook(lastID)
	if err != nil {
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(BookResponse{Book: *createdBook})
}

// ListBooksHandler handles listing books with optional author filter
func (s *BookService) ListBooksHandler(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	
	books, err := s.repo.ListBooks(author)
	if err != nil {
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(BooksResponse{Books: books})
}

// GetBookHandler handles retrieving a single book by ID
func (s *BookService) GetBookHandler(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error": "Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := s.repo.GetBook(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(BookResponse{Book: *book})
}

// UpdateBookHandler handles updating a book
func (s *BookService) UpdateBookHandler(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error": "Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	var req BookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "Invalid JSON"}`, http.StatusBadRequest)
		return
	}

	// Validation
	if req.Title == "" {
		http.Error(w, `{"error": "Title is required"}`, http.StatusBadRequest)
		return
	}
	if req.Author == "" {
		http.Error(w, `{"error": "Author is required"}`, http.StatusBadRequest)
		return
	}

	// Update the book
	book := &Book{
		ID:     id,
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	err = s.repo.UpdateBook(id, book)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	// Get the updated book to return it
	updatedBook, err := s.repo.GetBook(id)
	if err != nil {
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(BookResponse{Book: *updatedBook})
}

// DeleteBookHandler handles deleting a book
func (s *BookService) DeleteBookHandler(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error": "Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	err = s.repo.DeleteBook(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": "%s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNoContent)
}

func initDB() (*sql.DB, error) {
	_, filename, _, _ := runtime.Caller(0)
	dir := filepath.Dir(filename)
	dbPath := filepath.Join(dir, "books.db")

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, err
	}

	// Enable foreign keys
	_, err = db.Exec("PRAGMA foreign_keys = ON")
	if err != nil {
		db.Close()
		return nil, err
	}

	// Create books table
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT UNIQUE
	)`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		db.Close()
		return nil, err
	}

	return db, nil
}

func main() {
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	// Initialize the database
	db, err := initDB()
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer db.Close()

	// Initialize the repository
	repo := NewBookRepository(db)

	// Initialize the service
	service := NewBookService(repo)

	// Define routes
	r.Route("/books", func(r chi.Router) {
		r.Post("/", service.CreateBookHandler)
		r.Get("/", service.ListBooksHandler)
		r.Route("/{id}", func(r chi.Router) {
			r.Get("/", service.GetBookHandler)
			r.Put("/", service.UpdateBookHandler)
			r.Delete("/", service.DeleteBookHandler)
		})
	})

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}