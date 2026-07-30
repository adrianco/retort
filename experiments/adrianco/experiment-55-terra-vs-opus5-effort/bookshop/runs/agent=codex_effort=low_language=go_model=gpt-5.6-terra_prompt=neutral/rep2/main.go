package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
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
	_, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`)
	if err != nil {
		return nil, fmt.Errorf("create books table: %w", err)
	}
	return &API{db: db}, nil
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
			a.createBook(w, r)
		case http.MethodGet:
			a.listBooks(w, r)
		default:
			methodNotAllowed(w)
		}
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		idText := strings.TrimPrefix(r.URL.Path, "/books/")
		if idText == "" || strings.Contains(idText, "/") {
			writeError(w, http.StatusNotFound, "not found")
			return
		}
		id, err := strconv.ParseInt(idText, 10, 64)
		if err != nil || id < 1 {
			writeError(w, http.StatusNotFound, "not found")
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
	writeError(w, http.StatusNotFound, "not found")
}

func decodeBook(r *http.Request) (Book, error) {
	defer r.Body.Close()
	var book Book
	dec := json.NewDecoder(http.MaxBytesReader(nil, r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&book); err != nil {
		return book, errors.New("request body must be valid JSON")
	}
	if strings.TrimSpace(book.Title) == "" || strings.TrimSpace(book.Author) == "" {
		return book, errors.New("title and author are required")
	}
	book.Title, book.Author = strings.TrimSpace(book.Title), strings.TrimSpace(book.Author)
	return book, nil
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	result, err := a.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`, b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	b.ID, _ = result.LastInsertId()
	writeJSON(w, http.StatusCreated, b)
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query, args := `SELECT id, title, author, year, isbn FROM books`, []any{}
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`
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
	b, err := a.book(id)
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
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	result, err := a.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`, b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, http.StatusOK, b)
}

func (a *API) deleteBook(w http.ResponseWriter, id int64) {
	result, err := a.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (a *API) book(id int64) (Book, error) {
	var b Book
	err := a.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}
func methodNotAllowed(w http.ResponseWriter) {
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func main() {
	dsn := os.Getenv("BOOKS_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	db, err := sql.Open("sqlite3", dsn)
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
