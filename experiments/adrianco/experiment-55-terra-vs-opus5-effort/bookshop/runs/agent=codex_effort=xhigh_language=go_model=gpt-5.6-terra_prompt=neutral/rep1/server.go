package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
)

// Book is a book stored in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Server provides HTTP handlers backed by a SQLite database.
type Server struct {
	db *sql.DB
}

// NewServer creates the books table, if needed, and returns an HTTP handler.
func NewServer(db *sql.DB) (*Server, error) {
	if db == nil {
		return nil, errors.New("database must not be nil")
	}

	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL DEFAULT 0,
			isbn TEXT NOT NULL DEFAULT ''
		)
	`)
	if err != nil {
		return nil, fmt.Errorf("create books table: %w", err)
	}

	return &Server{db: db}, nil
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimSuffix(r.URL.Path, "/")
	if path == "" {
		path = "/"
	}

	switch {
	case r.Method == http.MethodGet && path == "/health":
		s.health(w, r)
	case path == "/books":
		s.books(w, r)
	case strings.HasPrefix(path, "/books/"):
		s.book(w, r, strings.TrimPrefix(path, "/books/"))
	default:
		writeError(w, http.StatusNotFound, "route not found")
	}
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.db.PingContext(r.Context()); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		s.createBook(w, r)
	case http.MethodGet:
		s.listBooks(w, r)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPost)
	}
}

func (s *Server) book(w http.ResponseWriter, r *http.Request, rawID string) {
	if rawID == "" || strings.Contains(rawID, "/") {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	id, err := strconv.ParseInt(rawID, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
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
		methodNotAllowed(w, http.MethodGet, http.MethodPut, http.MethodDelete)
	}
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	book, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	result, err := s.db.ExecContext(r.Context(),
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	book.ID, err = result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query := "SELECT id, title, author, year, isbn FROM books"
	args := []any{}
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}
	query += " ORDER BY id"

	rows, err := s.db.QueryContext(r.Context(), query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	defer rows.Close()

	books := make([]Book, 0)
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	book, err := s.findBook(r, id)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	book, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	result, err := s.db.ExecContext(r.Context(),
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	updated, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	if updated == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	book.ID = id
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	result, err := s.db.ExecContext(r.Context(), "DELETE FROM books WHERE id = ?", id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	deleted, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	if deleted == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) findBook(r *http.Request, id int64) (Book, error) {
	var book Book
	err := s.db.QueryRowContext(r.Context(),
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	return book, err
}

func decodeBook(r *http.Request) (Book, error) {
	defer r.Body.Close()
	decoder := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	decoder.DisallowUnknownFields()

	var book Book
	if err := decoder.Decode(&book); err != nil {
		return Book{}, errors.New("request body must be a valid book JSON object")
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return Book{}, errors.New("request body must contain one JSON object")
	}

	book.Title = strings.TrimSpace(book.Title)
	book.Author = strings.TrimSpace(book.Author)
	book.ISBN = strings.TrimSpace(book.ISBN)
	if book.Title == "" {
		return Book{}, errors.New("title is required")
	}
	if book.Author == "" {
		return Book{}, errors.New("author is required")
	}
	if book.Year < 0 || book.Year > 9999 {
		return Book{}, errors.New("year must be between 0 and 9999")
	}
	return book, nil
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func methodNotAllowed(w http.ResponseWriter, allowed ...string) {
	w.Header().Set("Allow", strings.Join(allowed, ", "))
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}
