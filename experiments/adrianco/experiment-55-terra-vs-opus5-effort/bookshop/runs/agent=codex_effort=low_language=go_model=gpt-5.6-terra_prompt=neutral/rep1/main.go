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

// Book is a record in the book collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type api struct{ db *sql.DB }

func newAPI(db *sql.DB) (*api, error) {
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
	return &api{db: db}, nil
}

func (a *api) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
	return mux
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query, args := "SELECT id, title, author, year, isbn FROM books", []any{}
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}
	query += " ORDER BY id"
	rows, err := a.db.Query(query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	defer rows.Close()
	books := make([]Book, 0)
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "database error")
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	result, err := a.db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	id, _ := result.LastInsertId()
	writeJSON(w, http.StatusCreated, Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
}

func (a *api) getBook(w http.ResponseWriter, r *http.Request) {
	b, found := a.findBook(w, r)
	if !found {
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) updateBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	result, err := a.db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", in.Title, in.Author, in.Year, in.ISBN, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	changed, _ := result.RowsAffected()
	if changed == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
}

func (a *api) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	result, err := a.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	changed, _ := result.RowsAffected()
	if changed == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (a *api) findBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	id, ok := parseID(w, r)
	if !ok {
		return Book{}, false
	}
	var b Book
	err := a.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return Book{}, false
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return Book{}, false
	}
	return b, true
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func decodeBook(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	de := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	de.DisallowUnknownFields()
	var in bookInput
	if err := de.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return in, false
	}
	in.Title, in.Author = strings.TrimSpace(in.Title), strings.TrimSpace(in.Author)
	if in.Title == "" || in.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return in, false
	}
	return in, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func main() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "books.db"
	}
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	service, err := newAPI(db)
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("book API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, service.routes()))
}
