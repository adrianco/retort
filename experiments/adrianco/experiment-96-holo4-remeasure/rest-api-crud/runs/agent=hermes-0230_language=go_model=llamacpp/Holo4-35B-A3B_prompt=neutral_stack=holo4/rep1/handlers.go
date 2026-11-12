package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

// booksRequest is the JSON body for creating/updating a book.
type booksRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// booksHandler handles GET /books and POST /books.
func booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		listBooks(w, r)
	case http.MethodPost:
		createBook(w, r)
	default:
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(w).Encode(map[string]string{"error": "method not allowed"})
	}
}

// bookHandler handles GET/PUT/DELETE /books/{id}.
func bookHandler(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	if idStr == "" {
		http.Error(w, `{"error":"book id required"}`, http.StatusBadRequest)
		return
	}
	id, err := strconv.Atoi(idStr)
	if err != nil || id <= 0 {
		http.Error(w, `{"error":"invalid book id"}`, http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		getBook(w, r, id)
	case http.MethodPut:
		updateBook(w, r, id)
	case http.MethodDelete:
		deleteBook(w, r, id)
	default:
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(w).Encode(map[string]string{"error": "method not allowed"})
	}
}

// listBooks returns all books, optionally filtered by author.
func listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")

	var books []Book
	if author != "" {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
		if err != nil {
			http.Error(w, `{"error":"database error"}`, http.StatusInternalServerError)
			return
		}
		defer rows.Close()
		books = scanBooks(rows)
	} else {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books")
		if err != nil {
			http.Error(w, `{"error":"database error"}`, http.StatusInternalServerError)
			return
		}
		defer rows.Close()
		books = scanBooks(rows)
	}
	if books == nil {
		books = []Book{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

// createBook creates a new book from the request body.
func createBook(w http.ResponseWriter, r *http.Request) {
	var req booksRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid JSON"})
		return
	}

	if err := validateBook(req.Title, req.Author); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		if errors.Is(err, sql.ErrConnDone) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]string{"error": "database error"})
			return
		}
		// Check for unique constraint violation on isbn
		if strings.Contains(err.Error(), "UNIQUE") {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusConflict)
			json.NewEncoder(w).Encode(map[string]string{"error": "isbn already exists"})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "database error"})
		return
	}

	id, _ := result.LastInsertId()
	book := Book{
		ID:     int(id),
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// getBook returns a single book by ID.
func getBook(w http.ResponseWriter, r *http.Request, id int) {
	var b Book
	err := db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN,
	)
	if err == sql.ErrNoRows {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "book not found"})
		return
	}
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "database error"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(b)
}

// updateBook updates an existing book.
func updateBook(w http.ResponseWriter, r *http.Request, id int) {
	var req booksRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid JSON"})
		return
	}

	if err := validateBook(req.Title, req.Author); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	result, err := db.Exec(
		"UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
		req.Title, req.Author, req.Year, req.ISBN, id,
	)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusConflict)
			json.NewEncoder(w).Encode(map[string]string{"error": "isbn already exists"})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "database error"})
		return
	}

	rows, _ := result.RowsAffected()
	if rows == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "book not found"})
		return
	}

	book := Book{
		ID:     id,
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// deleteBook deletes a book by ID.
func deleteBook(w http.ResponseWriter, r *http.Request, id int) {
	result, err := db.Exec("DELETE FROM books WHERE id=?", id)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "database error"})
		return
	}

	rows, _ := result.RowsAffected()
	if rows == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "book not found"})
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// validateBook checks that required fields are present.
func validateBook(title, author string) error {
	if strings.TrimSpace(title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

// resetDB drops and recreates the books table for a clean test state.
func resetDB() {
	db.Exec("DROP TABLE IF EXISTS books")
	db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`)
}

// scanBooks reads rows into a slice of Book.
func scanBooks(rows *sql.Rows) []Book {
	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			break
		}
		books = append(books, b)
	}
	return books
}
