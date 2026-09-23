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
			methodNotAllowed(w, http.MethodGet+", "+http.MethodPost)
		}
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		id, err := strconv.ParseInt(strings.TrimPrefix(r.URL.Path, "/books/"), 10, 64)
		if err != nil || id < 1 {
			writeError(w, http.StatusBadRequest, "invalid book id")
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
			methodNotAllowed(w, "GET, PUT, DELETE")
		}
		return
	}
	writeError(w, http.StatusNotFound, "not found")
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := decodeBook(w, r, &b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := validateBook(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	res, err := a.db.Exec(`INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	b.ID, _ = res.LastInsertId()
	writeJSON(w, http.StatusCreated, b)
}
func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query, args := `SELECT id,title,author,year,isbn FROM books ORDER BY id`, []any{}
	if author != "" {
		query = `SELECT id,title,author,year,isbn FROM books WHERE author = ? ORDER BY id`
		args = append(args, author)
	}
	rows, err := a.db.Query(query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	defer rows.Close()
	books := make([]Book, 0)
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
}
func (a *API) getBook(w http.ResponseWriter, id int64) {
	b, err := a.bookByID(id)
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
	if err := decodeBook(w, r, &b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := validateBook(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	res, err := a.db.Exec(`UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN, id)
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
}
func (a *API) deleteBook(w http.ResponseWriter, id int64) {
	res, err := a.db.Exec(`DELETE FROM books WHERE id=?`, id)
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
func (a *API) bookByID(id int64) (Book, error) {
	var b Book
	err := a.db.QueryRow(`SELECT id,title,author,year,isbn FROM books WHERE id=?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}
func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) error {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(b); err != nil {
		return fmt.Errorf("invalid JSON body")
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		return fmt.Errorf("request body must contain one JSON object")
	}
	return nil
}
func validateBook(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return errors.New("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return errors.New("author is required")
	}
	return nil
}
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
func methodNotAllowed(w http.ResponseWriter, allow string) {
	w.Header().Set("Allow", allow)
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func main() {
	path := os.Getenv("BOOKS_DB")
	if path == "" {
		path = "books.db"
	}
	db, err := sql.Open("sqlite3", path)
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
