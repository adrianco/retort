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

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func initialize(db *sql.DB) error {
	_, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`)
	return err
}

type server struct{ db *sql.DB }

func newServer(db *sql.DB) http.Handler {
	s := &server{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("/books", s.books)
	mux.HandleFunc("/books/", s.book)
	return mux
}

func (s *server) health(w http.ResponseWriter, _ *http.Request) {
	if err := s.db.Ping(); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) books(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/books" {
		http.NotFound(w, r)
		return
	}
	switch r.Method {
	case http.MethodPost:
		var b Book
		if !decodeBook(w, r, &b) {
			return
		}
		if err := validate(b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		err := s.db.QueryRow(`INSERT INTO books(title, author, year, isbn) VALUES(?, ?, ?, ?) RETURNING id`, b.Title, b.Author, b.Year, b.ISBN).Scan(&b.ID)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		writeJSON(w, http.StatusCreated, b)
	case http.MethodGet:
		query := `SELECT id, title, author, year, isbn FROM books`
		args := []any{}
		if author := strings.TrimSpace(r.URL.Query().Get("author")); author != "" {
			query += ` WHERE author = ?`
			args = append(args, author)
		}
		query += ` ORDER BY id`
		rows, err := s.db.Query(query, args...)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		defer rows.Close()
		books := []Book{}
		for rows.Next() {
			var b Book
			if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
				writeError(w, http.StatusInternalServerError, "could not read books")
				return
			}
			books = append(books, b)
		}
		if err := rows.Err(); err != nil {
			writeError(w, http.StatusInternalServerError, "could not read books")
			return
		}
		writeJSON(w, http.StatusOK, books)
	default:
		w.Header().Set("Allow", "GET, POST")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) book(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idText, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := findBook(s.db, id)
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not get book")
			return
		}
		writeJSON(w, http.StatusOK, b)
	case http.MethodPut:
		var b Book
		if !decodeBook(w, r, &b) {
			return
		}
		if err := validate(b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		res, err := s.db.Exec(`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`, b.Title, b.Author, b.Year, b.ISBN, id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not update book")
			return
		}
		n, err := res.RowsAffected()
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not update book")
			return
		}
		if n == 0 {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		b.ID = id
		writeJSON(w, http.StatusOK, b)
	case http.MethodDelete:
		res, err := s.db.Exec(`DELETE FROM books WHERE id=?`, id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not delete book")
			return
		}
		n, _ := res.RowsAffected()
		if n == 0 {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		w.Header().Set("Allow", "GET, PUT, DELETE")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func findBook(db *sql.DB, id int64) (Book, error) {
	var b Book
	err := db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id=?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func validate(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	if err := dec.Decode(&struct{}{}); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request must contain one JSON object")
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
