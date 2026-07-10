package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

type BookService struct {
	db *sql.DB
}

func NewBookService(db *sql.DB) *BookService {
	return &BookService{db: db}
}

// CreateBook handles POST /books
func (s *BookService) CreateBook(w http.ResponseWriter, r *http.Request) {
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

	// Insert book into database
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

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

// ListBooks handles GET /books with optional author filter
func (s *BookService) ListBooks(w http.ResponseWriter, r *http.Request) {
	var query string
	var args []interface{}

	author := r.URL.Query().Get("author")
	if author != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author = ?`
		args = append(args, author)
	} else {
		query = `SELECT id, title, author, year, isbn FROM books`
	}

	rows, err := s.db.Query(query, args...)
	if err != nil {
		http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			http.Error(w, "Failed to scan book", http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

// GetBook handles GET /books/{id}
func (s *BookService) GetBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	var book Book
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err = s.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
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

// UpdateBook handles PUT /books/{id}
func (s *BookService) UpdateBook(w http.ResponseWriter, r *http.Request) {
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

	// Update book in database
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	result, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		http.Error(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		http.Error(w, "Failed to get rows affected", http.StatusInternalServerError)
		return
	}

	if rowsAffected == 0 {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	// Return the updated book
	updatedBook, err := s.getBookByID(id)
	if err != nil {
		http.Error(w, "Failed to fetch updated book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(updatedBook)
}

// DeleteBook handles DELETE /books/{id}
func (s *BookService) DeleteBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Check if book exists
	var bookID int
	err = s.db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&bookID)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
			return
		}
		http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
		return
	}

	// Delete book from database
	query := `DELETE FROM books WHERE id = ?`
	result, err := s.db.Exec(query, id)
	if err != nil {
		http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		http.Error(w, "Failed to get rows affected", http.StatusInternalServerError)
		return
	}

	if rowsAffected == 0 {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// Helper function to get book by ID
func (s *BookService) getBookByID(id int) (Book, error) {
	var book Book
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err := s.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		return book, err
	}
	return book, nil
}