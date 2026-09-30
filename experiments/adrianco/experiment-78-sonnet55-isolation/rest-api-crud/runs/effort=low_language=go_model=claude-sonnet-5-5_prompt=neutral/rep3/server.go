package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
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

type Server struct{ db *sql.DB }

// NewServer opens the SQLite database at dsn and returns the HTTP handler.
func NewServer(dsn string) (*Server, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1) // keeps in-memory DBs consistent
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL, author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0, isbn TEXT NOT NULL DEFAULT '')`)
	if err != nil {
		return nil, err
	}
	return &Server{db: db}, nil
}

func (s *Server) Handler() http.Handler {
	m := http.NewServeMux()
	m.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := s.db.Ping(); err != nil {
			writeJSON(w, 503, map[string]string{"status": "unhealthy"})
			return
		}
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})
	m.HandleFunc("POST /books", s.create)
	m.HandleFunc("GET /books", s.list)
	m.HandleFunc("GET /books/{id}", s.get)
	m.HandleFunc("PUT /books/{id}", s.update)
	m.HandleFunc("DELETE /books/{id}", s.del)
	return m
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func decode(r *http.Request) (Book, string) {
	var b Book
	if err := json.NewDecoder(http.MaxBytesReader(nil, r.Body, 1<<20)).Decode(&b); err != nil {
		return b, "invalid JSON body"
	}
	b.Title, b.Author = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author)
	switch {
	case b.Title == "":
		return b, "title is required"
	case b.Author == "":
		return b, "author is required"
	case b.Year < 0:
		return b, "year must not be negative"
	}
	return b, ""
}

func pathID(r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	return id, err == nil && id > 0
}

func (s *Server) create(w http.ResponseWriter, r *http.Request) {
	b, msg := decode(r)
	if msg != "" {
		writeErr(w, 400, msg)
		return
	}
	res, err := s.db.Exec(`INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	b.ID, _ = res.LastInsertId()
	writeJSON(w, 201, b)
}

func (s *Server) list(w http.ResponseWriter, r *http.Request) {
	q, args := `SELECT id,title,author,year,isbn FROM books`, []any{}
	if a := r.URL.Query().Get("author"); a != "" {
		q += ` WHERE author = ?`
		args = append(args, a)
	}
	rows, err := s.db.Query(q+` ORDER BY id`, args...)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeErr(w, 500, "database error")
			return
		}
		books = append(books, b)
	}
	writeJSON(w, 200, books)
}

func (s *Server) get(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeErr(w, 400, "invalid id")
		return
	}
	var b Book
	err := s.db.QueryRow(`SELECT id,title,author,year,isbn FROM books WHERE id=?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		writeErr(w, 404, "book not found")
		return
	} else if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	writeJSON(w, 200, b)
}

func (s *Server) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeErr(w, 400, "invalid id")
		return
	}
	b, msg := decode(r)
	if msg != "" {
		writeErr(w, 400, msg)
		return
	}
	res, err := s.db.Exec(`UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeErr(w, 404, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, 200, b)
}

func (s *Server) del(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeErr(w, 400, "invalid id")
		return
	}
	res, err := s.db.Exec(`DELETE FROM books WHERE id=?`, id)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeErr(w, 404, "book not found")
		return
	}
	w.WriteHeader(204)
}
