package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

const defaultDatabasePath = "books.db"

func main() {
	databasePath := os.Getenv("BOOKS_DB")
	if databasePath == "" {
		databasePath = defaultDatabasePath
	}

	db, err := OpenDatabase(databasePath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer db.Close()

	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	server := &http.Server{
		Addr:              addr,
		Handler:           NewServer(db),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("book service listening on %s", addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("serve: %v", err)
	}
}

// OpenDatabase opens a SQLite database and ensures its schema exists.
func OpenDatabase(dataSourceName string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", dataSourceName)
	if err != nil {
		return nil, fmt.Errorf("open sqlite database: %w", err)
	}

	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("ping sqlite database: %w", err)
	}

	const schema = `
		CREATE TABLE IF NOT EXISTS books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL DEFAULT 0,
			isbn TEXT NOT NULL DEFAULT ''
		);`
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create books schema: %w", err)
	}
	return db, nil
}

// NewServer returns the HTTP API handler using db for persistence.
func NewServer(db *sql.DB) http.Handler {
	return &api{db: db}
}

type api struct {
	db *sql.DB
}

func (a *api) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch {
	case r.URL.Path == "/health":
		a.health(w, r)
	case r.URL.Path == "/books":
		a.books(w, r)
	case strings.HasPrefix(r.URL.Path, "/books/"):
		a.book(w, r)
	default:
		writeError(w, http.StatusNotFound, "route not found")
	}
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w, http.MethodGet)
		return
	}
	if err := a.db.PingContext(r.Context()); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		a.createBook(w, r)
	case http.MethodGet:
		a.listBooks(w, r)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPost)
	}
}

func (a *api) book(w http.ResponseWriter, r *http.Request) {
	id, ok := parseBookID(r.URL.Path)
	if !ok {
		writeError(w, http.StatusNotFound, "book not found")
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
}

func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	input, err := decodeBookInput(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	result, err := a.db.ExecContext(r.Context(),
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	id, err := result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, Book{ID: id, BookInput: input})
}

func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query := `SELECT id, title, author, year, isbn FROM books`
	args := []any{}
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := a.db.QueryContext(ctx, query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	defer rows.Close()

	books := make([]Book, 0)
	for rows.Next() {
		book, err := scanBook(rows)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *api) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	book, err := a.findBook(r.Context(), id)
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

func (a *api) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	input, err := decodeBookInput(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	result, err := a.db.ExecContext(r.Context(),
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		input.Title, input.Author, input.Year, input.ISBN, id)
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
	writeJSON(w, http.StatusOK, Book{ID: id, BookInput: input})
}

func (a *api) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	result, err := a.db.ExecContext(r.Context(), `DELETE FROM books WHERE id = ?`, id)
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

func (a *api) findBook(ctx context.Context, id int64) (Book, error) {
	row := a.db.QueryRowContext(ctx, `SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	return scanBook(row)
}
