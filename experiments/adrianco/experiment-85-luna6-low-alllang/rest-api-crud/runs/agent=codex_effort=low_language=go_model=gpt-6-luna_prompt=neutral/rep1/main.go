package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
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

func openDB(dsn string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(`PRAGMA foreign_keys = ON; CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func NewAPI(db *sql.DB) *API { return &API{db: db} }

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			methodNotAllowed(w)
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		switch r.Method {
		case http.MethodGet:
			a.listBooks(w, r)
		case http.MethodPost:
			a.createBook(w, r)
		default:
			methodNotAllowed(w)
		}
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		id, err := strconv.ParseInt(strings.TrimPrefix(r.URL.Path, "/books/"), 10, 64)
		if err != nil || id < 1 {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		switch r.Method {
		case http.MethodGet:
			a.getBook(w, id)
		case http.MethodPut:
			a.updateBook(w, r, id)
		case http.MethodDelete:
			a.deleteBook(w, id)
		default:
			methodNotAllowed(w)
		}
		return
	}
	http.NotFound(w, r)
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if !decodeBook(w, r, &b) {
		return
	}
	res, err := a.db.Exec(`INSERT INTO books(title, author, year, isbn) VALUES(?, ?, ?, ?)`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN)
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
	var rows *sql.Rows
	var err error
	if author := strings.TrimSpace(r.URL.Query().Get("author")); author != "" {
		rows, err = a.db.Query(`SELECT id,title,author,year,isbn FROM books WHERE author = ? ORDER BY id`, author)
	} else {
		rows, err = a.db.Query(`SELECT id,title,author,year,isbn FROM books ORDER BY id`)
	}
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

func (a *API) getBook(w http.ResponseWriter, id int64) {
	b, err := scanBook(a.db.QueryRow(`SELECT id,title,author,year,isbn FROM books WHERE id = ?`, id))
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
	var b Book
	if !decodeBook(w, r, &b) {
		return
	}
	res, err := a.db.Exec(`UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN, id)
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

func (a *API) deleteBook(w http.ResponseWriter, id int64) {
	res, err := a.db.Exec(`DELETE FROM books WHERE id=?`, id)
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

type rowScanner interface{ Scan(...any) error }

func scanBook(row rowScanner) (Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	if err := d.Decode(b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	var extra any
	if err := d.Decode(&extra); err == nil {
		writeError(w, http.StatusBadRequest, "request must contain one JSON object")
		return false
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
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
func methodNotAllowed(w http.ResponseWriter) {
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func main() {
	dsn := os.Getenv("DATABASE_PATH")
	if dsn == "" {
		dsn = "books.db"
	}
	db, err := openDB(dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	server := &http.Server{Addr: addr, Handler: NewAPI(db)}
	log.Printf("book API listening on %s", addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(fmt.Errorf("server: %w", err))
	}
}

// Ensure the DB can be checked by callers that want to verify readiness.
func (a *API) ping(ctx context.Context) error { return a.db.PingContext(ctx) }
