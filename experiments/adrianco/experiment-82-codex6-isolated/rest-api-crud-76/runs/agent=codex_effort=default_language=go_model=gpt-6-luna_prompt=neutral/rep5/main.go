package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type API struct{ db *sql.DB }

func NewAPI(db *sql.DB) (*API, error) {
	if db == nil {
		return nil, errors.New("database is required")
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`); err != nil {
		return nil, fmt.Errorf("create books table: %w", err)
	}
	return &API{db: db}, nil
}

func (a *API) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := a.db.PingContext(r.Context()); err != nil {
			writeError(w, http.StatusServiceUnavailable, "database unavailable")
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/books", a.books)
	mux.HandleFunc("/books/", a.bookByID)
	return mux
}

func (a *API) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		var b Book
		if !decodeBook(w, r, &b) {
			return
		}
		if !validBook(w, b) {
			return
		}
		res, err := a.db.ExecContext(r.Context(), `INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		b.ID, err = res.LastInsertId()
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		writeJSON(w, http.StatusCreated, b)
	case http.MethodGet:
		a.listBooks(w, r)
	default:
		w.Header().Set("Allow", "GET, POST")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query, args := `SELECT id,title,author,year,isbn FROM books ORDER BY id`, []any{}
	if author != "" {
		query = `SELECT id,title,author,year,isbn FROM books WHERE author = ? ORDER BY id`
		args = append(args, author)
	}
	rows, err := a.db.QueryContext(r.Context(), query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	defer rows.Close()
	books := make([]Book, 0)
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) bookByID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodPut && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "GET, PUT, DELETE")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	id := strings.TrimPrefix(r.URL.Path, "/books/")
	var b Book
	switch r.Method {
	case http.MethodGet:
		if err := a.db.QueryRowContext(r.Context(), `SELECT id,title,author,year,isbn FROM books WHERE id = ?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			notFoundOrError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, b)
	case http.MethodPut:
		if !decodeBook(w, r, &b) {
			return
		}
		if !validBook(w, b) {
			return
		}
		res, err := a.db.ExecContext(r.Context(), `UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN, id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not update book")
			return
		}
		n, _ := res.RowsAffected()
		if n == 0 {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err := a.db.QueryRowContext(r.Context(), `SELECT id,title,author,year,isbn FROM books WHERE id=?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "could not retrieve book")
			return
		}
		writeJSON(w, http.StatusOK, b)
	case http.MethodDelete:
		res, err := a.db.ExecContext(r.Context(), `DELETE FROM books WHERE id=?`, id)
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
	}
}

func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) bool {
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request must contain one JSON object")
		return false
	}
	return true
}
func validBook(w http.ResponseWriter, b Book) bool {
	if strings.TrimSpace(b.Title) == "" || strings.TrimSpace(b.Author) == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return false
	}
	return true
}
func notFoundOrError(w http.ResponseWriter, err error) {
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
	} else {
		writeError(w, http.StatusInternalServerError, "could not retrieve book")
	}
}
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func main() {
	path := os.Getenv("DB_PATH")
	if path == "" {
		path = "books.db"
	}
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	api, err := NewAPI(db)
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("book API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, api.Routes()))
}
