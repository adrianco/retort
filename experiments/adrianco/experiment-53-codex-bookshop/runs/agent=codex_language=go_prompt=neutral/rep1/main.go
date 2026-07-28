package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type Store struct{ db *sql.DB }

func OpenStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	if _, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`); err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) Create(ctx context.Context, in bookInput) (Book, error) {
	r, err := s.db.ExecContext(ctx, "INSERT INTO books(title, author, year, isbn) VALUES(?, ?, ?, ?)", in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		return Book{}, err
	}
	id, err := r.LastInsertId()
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, err
}

func scanBook(row *sql.Row) (Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	return scanBook(s.db.QueryRowContext(ctx, "SELECT id, title, author, year, isbn FROM books WHERE id = ?", id))
}

func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query, args := "SELECT id, title, author, year, isbn FROM books", []any{}
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}
	query += " ORDER BY id"
	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	books := make([]Book, 0)
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func (s *Store) Update(ctx context.Context, id int64, in bookInput) (Book, error) {
	r, err := s.db.ExecContext(ctx, "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", in.Title, in.Author, in.Year, in.ISBN, id)
	if err != nil {
		return Book{}, err
	}
	n, err := r.RowsAffected()
	if err != nil {
		return Book{}, err
	}
	if n == 0 {
		return Book{}, sql.ErrNoRows
	}
	return s.Get(ctx, id)
}

func (s *Store) Delete(ctx context.Context, id int64) error {
	r, err := s.db.ExecContext(ctx, "DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return err
	}
	n, err := r.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}

type Server struct{ store *Store }

func (s *Server) Handler() http.Handler { return http.HandlerFunc(s.handle) }

func (s *Server) handle(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			methodNotAllowed(w)
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		s.handleBooks(w, r)
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		s.handleBook(w, r)
		return
	}
	writeError(w, http.StatusNotFound, "not found")
}

func (s *Server) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		in, ok := decodeInput(w, r)
		if !ok {
			return
		}
		b, err := s.store.Create(r.Context(), in)
		if err != nil {
			writeError(w, 500, "internal server error")
			return
		}
		writeJSON(w, http.StatusCreated, b)
	case http.MethodGet:
		books, err := s.store.List(r.Context(), r.URL.Query().Get("author"))
		if err != nil {
			writeError(w, 500, "internal server error")
			return
		}
		writeJSON(w, http.StatusOK, books)
	default:
		methodNotAllowed(w)
	}
}

func (s *Server) handleBook(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idText, 10, 64)
	if idText == "" || err != nil || id <= 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := s.store.Get(r.Context(), id)
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, 404, "book not found")
			return
		}
		if err != nil {
			writeError(w, 500, "internal server error")
			return
		}
		writeJSON(w, 200, b)
	case http.MethodPut:
		in, ok := decodeInput(w, r)
		if !ok {
			return
		}
		b, err := s.store.Update(r.Context(), id, in)
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, 404, "book not found")
			return
		}
		if err != nil {
			writeError(w, 500, "internal server error")
			return
		}
		writeJSON(w, 200, b)
	case http.MethodDelete:
		err := s.store.Delete(r.Context(), id)
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, 404, "book not found")
			return
		}
		if err != nil {
			writeError(w, 500, "internal server error")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		methodNotAllowed(w)
	}
}

func decodeInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(&in); err != nil {
		writeError(w, 400, "request body must be valid JSON")
		return in, false
	}
	if strings.TrimSpace(in.Title) == "" || strings.TrimSpace(in.Author) == "" {
		writeError(w, 400, "title and author are required")
		return in, false
	}
	in.Title, in.Author = strings.TrimSpace(in.Title), strings.TrimSpace(in.Author)
	return in, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func methodNotAllowed(w http.ResponseWriter) {
	w.Header().Set("Allow", "GET, POST, PUT, DELETE")
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func main() {
	dsn := os.Getenv("BOOKS_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	store, err := OpenStore(dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer store.Close()
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("books API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, (&Server{store: store}).Handler()))
}
