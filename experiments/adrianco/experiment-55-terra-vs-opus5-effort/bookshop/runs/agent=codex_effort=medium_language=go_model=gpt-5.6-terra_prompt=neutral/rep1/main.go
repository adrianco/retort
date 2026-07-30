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
	"time"

	_ "modernc.org/sqlite"
)

// Book is a book stored in the collection. ID is assigned by the database.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type api struct{ db *sql.DB }

func newAPI(db *sql.DB) (*api, error) {
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL DEFAULT 0,
        isbn TEXT NOT NULL DEFAULT ''
    )`); err != nil {
		return nil, fmt.Errorf("create books table: %w", err)
	}
	return &api{db: db}, nil
}

func (a *api) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("GET /books", a.books)
	mux.HandleFunc("POST /books", a.books)
	mux.HandleFunc("GET /books/{id}", a.book)
	mux.HandleFunc("PUT /books/{id}", a.book)
	mux.HandleFunc("DELETE /books/{id}", a.book)
	return mux
}

func (a *api) health(w http.ResponseWriter, _ *http.Request) {
	if err := a.db.Ping(); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		var b Book
		if !decodeBook(w, r, &b) {
			return
		}
		result, err := a.db.ExecContext(r.Context(), "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", b.Title, b.Author, b.Year, b.ISBN)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		b.ID, _ = result.LastInsertId()
		writeJSON(w, http.StatusCreated, b)
	case http.MethodGet:
		author := strings.TrimSpace(r.URL.Query().Get("author"))
		query, args := "SELECT id, title, author, year, isbn FROM books", []any{}
		if author != "" {
			query += " WHERE author = ?"
			args = append(args, author)
		}
		query += " ORDER BY id"
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
}

func (a *api) book(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := a.find(r.Context(), id)
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
		result, err := a.db.ExecContext(r.Context(), "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", b.Title, b.Author, b.Year, b.ISBN, id)
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
	case http.MethodDelete:
		result, err := a.db.ExecContext(r.Context(), "DELETE FROM books WHERE id = ?", id)
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
}

func (a *api) find(ctx context.Context, id int64) (Book, error) {
	var b Book
	err := a.db.QueryRowContext(ctx, "SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) bool {
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	b.Title, b.Author = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
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
	service, err := newAPI(db)
	if err != nil {
		log.Fatal(err)
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	server := &http.Server{Addr: ":" + port, Handler: service.routes(), ReadHeaderTimeout: 5 * time.Second}
	log.Printf("book service listening on :%s", port)
	log.Fatal(server.ListenAndServe())
}
