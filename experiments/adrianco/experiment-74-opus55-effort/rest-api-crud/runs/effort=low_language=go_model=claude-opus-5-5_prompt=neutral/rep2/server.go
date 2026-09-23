package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type Server struct {
	db  *sql.DB
	mux *http.ServeMux
}

func NewServer(db *sql.DB) (*Server, error) {
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT)`); err != nil {
		return nil, err
	}
	s := &Server{db: db, mux: http.NewServeMux()}
	s.mux.HandleFunc("GET /health", s.health)
	s.mux.HandleFunc("POST /books", s.create)
	s.mux.HandleFunc("GET /books", s.list)
	s.mux.HandleFunc("GET /books/{id}", s.get)
	s.mux.HandleFunc("PUT /books/{id}", s.update)
	s.mux.HandleFunc("DELETE /books/{id}", s.delete)
	return s, nil
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) { s.mux.ServeHTTP(w, r) }

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func decodeBook(w http.ResponseWriter, r *http.Request) (*Book, bool) {
	var b Book
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&b); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return nil, false
	}
	b.Title, b.Author, b.ISBN = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), strings.TrimSpace(b.ISBN)
	var missing []string
	if b.Title == "" {
		missing = append(missing, "title")
	}
	if b.Author == "" {
		missing = append(missing, "author")
	}
	if len(missing) > 0 {
		writeErr(w, http.StatusBadRequest, strings.Join(missing, " and ")+" required")
		return nil, false
	}
	if b.Year < 0 || b.Year > 9999 {
		writeErr(w, http.StatusBadRequest, "year must be between 0 and 9999")
		return nil, false
	}
	return &b, true
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeErr(w, http.StatusBadRequest, "invalid id")
		return 0, false
	}
	return id, true
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.db.PingContext(r.Context()); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unhealthy"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) create(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`, b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	b.ID, _ = res.LastInsertId()
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) list(w http.ResponseWriter, r *http.Request) {
	q := `SELECT id, title, author, COALESCE(year,0), COALESCE(isbn,'') FROM books`
	var args []any
	if a := r.URL.Query().Get("author"); a != "" {
		q += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, a)
	}
	rows, err := s.db.Query(q+` ORDER BY id`, args...)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeErr(w, http.StatusInternalServerError, "database error")
			return
		}
		books = append(books, b)
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) get(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, COALESCE(year,0), COALESCE(isbn,'') FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) update(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`, b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`DELETE FROM books WHERE id=?`, id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
