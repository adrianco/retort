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
		return Book{}, err
	}
	return book, nil
}

func (bs *BookStore) GetBooks(author string) ([]Book, error) {
	var query string
	var rows *sql.Rows
	var err error

	if author != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY id`
		rows, err = bs.db.Query(query, "%"+author+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books ORDER BY id`
		rows, err = bs.db.Query(query)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err = rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}

	return books, nil
}

func (bs *BookStore) GetBook(id int) (*Book, error) {
	var book Book
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err := bs.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		return nil, err
	}
	return &book, nil
}

func (bs *BookStore) UpdateBook(id int, book Book) error {
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err := bs.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	return err
}

func (bs *BookStore) DeleteBook(id int) error {
	query := `DELETE FROM books WHERE id = ?`
	_, err := bs.db.Exec(query, id)
	return err
}

func (bs *BookStore) HealthCheck() error {
	query := `SELECT 1`
	return bs.db.QueryRow(query).Err()
}

func respondWithJSON(w http.ResponseWriter, code int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(payload)
}

func (bs *BookStore) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid JSON"})
		return
	}

	// Validation
	if book.Title == "" {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Title is required"})
		return
	}
	if book.Author == "" {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Author is required"})
		return
	}

	createdBook, err := bs.CreateBook(book)
	if err != nil {
		respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to create book"})
		return
	}

	respondWithJSON(w, http.StatusCreated, createdBook)
}

func (bs *BookStore) handleGetBooks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}

	author := r.URL.Query().Get("author")
	books, err := bs.GetBooks(author)
	if err != nil {
		respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to fetch books"})
		return
	}

	respondWithJSON(w, http.StatusOK, books)
}

func (bs *BookStore) handleGetBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}

	// Extract ID from URL path
	pathParts := strings.Split(r.URL.Path, "/")
	if len(pathParts) < 3 {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid URL"})
		return
	}
	id, err := strconv.Atoi(pathParts[2])
	if err != nil {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid book ID"})
		return
	}

	book, err := bs.GetBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			respondWithJSON(w, http.StatusNotFound, map[string]string{"error": "Book not found"})
		} else {
			respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to fetch book"})
		}
		return
	}

	respondWithJSON(w, http.StatusOK, book)
}

func (bs *BookStore) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}

	// Extract ID from URL path
	pathParts := strings.Split(r.URL.Path, "/")
	if len(pathParts) < 3 {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid URL"})
		return
	}
	id, err := strconv.Atoi(pathParts[2])
	if err != nil {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid book ID"})
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid JSON"})
		return
	}

	// Validation
	if book.Title == "" {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Title is required"})
		return
	}
	if book.Author == "" {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Author is required"})
		return
	}

	err = bs.UpdateBook(id, book)
	if err != nil {
		if err == sql.ErrNoRows {
			respondWithJSON(w, http.StatusNotFound, map[string]string{"error": "Book not found"})
		} else {
			respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to update book"})
		}
		return
	}

	respondWithJSON(w, http.StatusOK, map[string]string{"message": "Book updated successfully"})
}

func (bs *BookStore) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}

	// Extract ID from URL path
	pathParts := strings.Split(r.URL.Path, "/")
	if len(pathParts) < 3 {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid URL"})
		return
	}
	id, err := strconv.Atoi(pathParts[2])
	if err != nil {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid book ID"})
		return
	}

	err = bs.DeleteBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			respondWithJSON(w, http.StatusNotFound, map[string]string{"error": "Book not found"})
		} else {
			respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to delete book"})
		}
		return
	}

	respondWithJSON(w, http.StatusOK, map[string]string{"message": "Book deleted successfully"})
}

func (bs *BookStore) handleHealthCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}

	err := bs.HealthCheck()
	if err != nil {
		respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Database connection failed"})
		return
	}

	respondWithJSON(w, http.StatusOK, map[string]string{"status": "healthy"})
}

func main() {
	// Initialize database
	dbPath := "./books.db"
	store, err := NewBookStore(dbPath)
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer store.Close()

	// Set up routes using a custom handler to differentiate by method
	http.HandleFunc("/health", store.handleHealthCheck)
	
	// Handle books endpoint with method differentiation
	http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			store.handleGetBooks(w, r)
		case http.MethodPost:
			store.handleCreateBook(w, r)
		default:
			respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		}
	})

	// Handle book by ID endpoint with method differentiation
	http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		// Extract ID from URL path
		pathParts := strings.Split(r.URL.Path, "/")
		if len(pathParts) < 3 {
			respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid URL"})
			return
		}
		id, err := strconv.Atoi(pathParts[2])
		if err != nil {
			respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid book ID"})
			return
		}

		switch r.Method {
		case http.MethodGet:
			store.handleGetBookWithID(w, r, id)
		case http.MethodPut:
			store.handleUpdateBookWithID(w, r, id)
		case http.MethodDelete:
			store.handleDeleteBookWithID(w, r, id)
		default:
			respondWithJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		}
	})
	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	
	fmt.Printf("Server starting on port %s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
func (bs *BookStore) handleGetBookWithID(w http.ResponseWriter, r *http.Request, id int) {
	book, err := bs.GetBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			respondWithJSON(w, http.StatusNotFound, map[string]string{"error": "Book not found"})
		} else {
			respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to fetch book"})
		}
		return
	}

	respondWithJSON(w, http.StatusOK, book)
}

func (bs *BookStore) handleUpdateBookWithID(w http.ResponseWriter, r *http.Request, id int) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid JSON"})
		return
	}

	// Validation
	if book.Title == "" {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Title is required"})
		return
	}
	if book.Author == "" {
		respondWithJSON(w, http.StatusBadRequest, map[string]string{"error": "Author is required"})
		return
	}

	err := bs.UpdateBook(id, book)
	if err != nil {
		if err == sql.ErrNoRows {
			respondWithJSON(w, http.StatusNotFound, map[string]string{"error": "Book not found"})
		} else {
			respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to update book"})
		}
		return
	}

	respondWithJSON(w, http.StatusOK, map[string]string{"message": "Book updated successfully"})
}

func (bs *BookStore) handleDeleteBookWithID(w http.ResponseWriter, r *http.Request, id int) {
	err := bs.DeleteBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			respondWithJSON(w, http.StatusNotFound, map[string]string{"error": "Book not found"})
		} else {
			respondWithJSON(w, http.StatusInternalServerError, map[string]string{"error": "Failed to delete book"})
		}
		return
	}

	respondWithJSON(w, http.StatusOK, map[string]string{"message": "Book deleted successfully"})
}