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
		return nil, fmt.Errorf("initialize books table: %w", err)
	}
	return &API{db: db}, nil
}

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			methodNotAllowed(w, http.MethodGet)
			return
		}
		if err := a.db.PingContext(r.Context()); err != nil {
			writeError(w, http.StatusServiceUnavailable, "database unavailable")
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		switch r.Method {
		case http.MethodPost:
			a.createBook(w, r)
		case http.MethodGet:
			a.listBooks(w, r)
		default:
			methodNotAllowed(w, http.MethodGet, http.MethodPost)
		}
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		id, err := strconv.ParseInt(strings.TrimPrefix(r.URL.Path, "/books/"), 10, 64)
		if err != nil || id < 1 {
			writeError(w, http.StatusBadRequest, "invalid book ID")
			return
		}
		switch r.Method {
		case http.MethodGet:
			a.getBook(w, r, id)
		case http.MethodPut:
			a.updateBook(w, r, id)
		case http.MethodDelete:
			a.deleteBook(w, r, id)
		default:
			methodNotAllowed(w, http.MethodGet, http.MethodPut, http.MethodDelete)
		}
		return
	}
	http.NotFound(w, r)
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := a.db.ExecContext(r.Context(), `INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, b.Title, b.Author, b.Year, b.ISBN)
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
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	query := `SELECT id,title,author,year,isbn FROM books`
	args := []any{}
	if author := strings.TrimSpace(r.URL.Query().Get("author")); author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`
	rows, err := a.db.QueryContext(r.Context(), query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err = rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		books = append(books, b)
	}
	if err = rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	b, err := scanBook(a.db.QueryRowContext(r.Context(), `SELECT id,title,author,year,isbn FROM books WHERE id=?`, id))
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := a.db.ExecContext(r.Context(), `UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, b.Title, b.Author, b.Year, b.ISBN, id)
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
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	res, err := a.db.ExecContext(r.Context(), `DELETE FROM books WHERE id=?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	n, err := res.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var b Book
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return b, false
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request must contain one JSON object")
		return b, false
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return b, false
	}
	if b.Year < 0 {
		writeError(w, http.StatusBadRequest, "year must be zero or greater")
		return b, false
	}
	return b, true
}

type rowScanner interface{ Scan(...any) error }

func scanBook(row rowScanner) (Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func methodNotAllowed(w http.ResponseWriter, methods ...string) {
	w.Header().Set("Allow", strings.Join(methods, ", "))
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func main() {
	dsn := os.Getenv("BOOKS_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	db.SetMaxOpenConns(1)
	api, err := NewAPI(db)
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("book API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, api))
}
