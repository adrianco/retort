package main

import (
	"context"
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
	"time"

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

func OpenDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	db.SetConnMaxLifetime(time.Hour)
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

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
		case http.MethodPost:
			a.create(w, r)
		case http.MethodGet:
			a.list(w, r)
		default:
			methodNotAllowed(w)
		}
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		a.book(w, r)
		return
	}
	http.NotFound(w, r)
}

func (a *API) create(w http.ResponseWriter, r *http.Request) {
	var b Book
	if !decodeBook(w, r, &b) {
		return
	}
	if err := validate(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	res, err := a.db.ExecContext(r.Context(), `INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, strings.TrimSpace(b.ISBN))
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

func (a *API) list(w http.ResponseWriter, r *http.Request) {
	query, args := `SELECT id,title,author,year,isbn FROM books`, []any{}
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

func (a *API) book(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/books/")
	if strings.Contains(idText, "/") || idText == "" {
		http.NotFound(w, r)
		return
	}
	id, err := strconv.ParseInt(idText, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := a.get(r.Context(), id)
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
		res, err := a.db.ExecContext(r.Context(), `UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, strings.TrimSpace(b.ISBN), id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not update book")
			return
		}
		n, _ := res.RowsAffected()
		if n == 0 {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		b.ID = id
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
	default:
		methodNotAllowed(w)
	}
}

func (a *API) get(ctx context.Context, id int64) (Book, error) {
	var b Book
	err := a.db.QueryRowContext(ctx, `SELECT id,title,author,year,isbn FROM books WHERE id=?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func validate(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return errors.New("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return errors.New("author is required")
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
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
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
	path := os.Getenv("BOOKS_DB")
	if path == "" {
		path = "books.db"
	}
	db, err := OpenDB(path)
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
	log.Fatal(http.ListenAndServe(addr, api))
}
