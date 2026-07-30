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

// Book is a book in the collection. Year is optional; zero means it was not supplied.
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

type api struct {
	db *sql.DB
}

// OpenDatabase opens a SQLite database and ensures its schema exists.
func OpenDatabase(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`)
	if err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

// NewHandler builds the HTTP API using the provided initialized SQLite database.
func NewHandler(db *sql.DB) http.Handler {
	a := &api{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
	return mux
}

func (a *api) health(w http.ResponseWriter, _ *http.Request) {
	if err := a.db.Ping(); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	result, err := a.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`, in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	id, err := result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
}

func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query := `SELECT id, title, author, year, isbn FROM books`
	args := []any{}
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
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "could not read books")
			return
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "could not read books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *api) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	book, err := a.findBook(id)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *api) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	result, err := a.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`, in.Title, in.Author, in.Year, in.ISBN, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	changed, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	if changed == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeJSON(w, http.StatusOK, Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
}

func (a *api) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	result, err := a.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	changed, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	if changed == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (a *api) findBook(id int64) (Book, error) {
	var book Book
	err := a.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	return book, err
}

func decodeBookInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	defer r.Body.Close()
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	decoder.DisallowUnknownFields()
	var in bookInput
	if err := decoder.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "request body must be valid JSON")
		return bookInput{}, false
	}
	if decoder.Decode(&struct{}{}) != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain one JSON object")
		return bookInput{}, false
	}
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	if in.Title == "" || in.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return bookInput{}, false
	}
	return in, true
}

func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(value); err != nil {
		log.Printf("writing JSON response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func main() {
	path := os.Getenv("DATABASE_PATH")
	if path == "" {
		path = "books.db"
	}
	db, err := OpenDatabase(path)
	if err != nil {
		log.Fatalf("opening database: %v", err)
	}
	defer db.Close()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	address := fmt.Sprintf(":%s", port)
	log.Printf("book API listening on %s", address)
	if err := http.ListenAndServe(address, NewHandler(db)); err != nil {
		log.Fatal(err)
	}
}
