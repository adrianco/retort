package main

import (
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

// Book is a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Server holds the database and serves the HTTP API.
type Server struct {
	db *sql.DB
}

// NewServer opens the database at dsn and ensures the schema exists.
func NewServer(dsn string) (*Server, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1) // keeps in-memory DBs consistent and avoids lock errors
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`)
	if err != nil {
		db.Close()
		return nil, err
	}
	return &Server{db: db}, nil
}

func (s *Server) Close() error { return s.db.Close() }

// Handler returns the routed HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := s.db.Ping(); err != nil {
			writeError(w, http.StatusServiceUnavailable, "database unavailable")
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var b Book
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return b, false
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	switch {
	case b.Title == "":
		writeError(w, http.StatusBadRequest, "title is required")
	case b.Author == "":
		writeError(w, http.StatusBadRequest, "author is required")
	case b.Year < 0:
		writeError(w, http.StatusBadRequest, "year must not be negative")
	default:
		return b, true
	}
	return b, false
}

func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid id")
		return 0, false
	}
	return id, true
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	b.ID, _ = res.LastInsertId()
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	q := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if a := r.URL.Query().Get("author"); a != "" {
		q += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, a)
	}
	rows, err := s.db.Query(q+` ORDER BY id`, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "database error")
			return
		}
		books = append(books, b)
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func main() {
	dsn := os.Getenv("DB_PATH")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	s, err := NewServer(dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer s.Close()
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, s.Handler()))
}
