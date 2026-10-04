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
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

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

type API struct{ db *sql.DB }

func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`PRAGMA busy_timeout = 5000;
 CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL CHECK(length(trim(title)) > 0),
 author TEXT NOT NULL CHECK(length(trim(author)) > 0),
 year INTEGER NOT NULL DEFAULT 0,
 isbn TEXT NOT NULL DEFAULT ''
 );`)
	if err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func respond(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if value != nil {
		_ = json.NewEncoder(w).Encode(value)
	}
}

func fail(w http.ResponseWriter, status int, message string) {
	respond(w, status, map[string]string{"error": message})
}

func methodNotAllowed(w http.ResponseWriter, allowed string) {
	w.Header().Set("Allow", allowed)
	fail(w, http.StatusMethodNotAllowed, "method not allowed")
}

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			methodNotAllowed(w, "GET")
			return
		}
		if err := a.db.PingContext(r.Context()); err != nil {
			fail(w, 503, "database unavailable")
			return
		}
		respond(w, 200, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		switch r.Method {
		case http.MethodGet:
			a.list(w, r)
		case http.MethodPost:
			a.save(w, r, 0)
		default:
			methodNotAllowed(w, "GET, POST")
		}
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") && !strings.Contains(strings.TrimPrefix(r.URL.Path, "/books/"), "/") {
		id, err := strconv.ParseInt(strings.TrimPrefix(r.URL.Path, "/books/"), 10, 64)
		if err != nil || id <= 0 {
			fail(w, 400, "id must be a positive integer")
			return
		}
		switch r.Method {
		case http.MethodGet:
			b, err := a.get(r.Context(), id)
			if a.dbError(w, err) {
				return
			}
			respond(w, 200, b)
		case http.MethodPut:
			a.save(w, r, id)
		case http.MethodDelete:
			result, err := a.db.ExecContext(r.Context(), "DELETE FROM books WHERE id = ?", id)
			if a.dbError(w, err) {
				return
			}
			n, err := result.RowsAffected()
			if a.dbError(w, err) {
				return
			}
			if n == 0 {
				fail(w, 404, "book not found")
				return
			}
			w.WriteHeader(http.StatusNoContent)
		default:
			methodNotAllowed(w, "GET, PUT, DELETE")
		}
		return
	}
	fail(w, 404, "route not found")
}

func (a *API) dbError(w http.ResponseWriter, err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, sql.ErrNoRows) {
		fail(w, 404, "book not found")
	} else {
		log.Printf("database error: %v", err)
		fail(w, 500, "database operation failed")
	}
	return true
}

func (a *API) get(ctx context.Context, id int64) (Book, error) {
	var b Book
	err := a.db.QueryRowContext(ctx, "SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func (a *API) list(w http.ResponseWriter, r *http.Request) {
	query := "SELECT id, title, author, year, isbn FROM books"
	args := []any{}
	if author, present := r.URL.Query()["author"]; present {
		query += " WHERE author = ?"
		args = append(args, author[0])
	}
	rows, err := a.db.QueryContext(r.Context(), query+" ORDER BY id", args...)
	if a.dbError(w, err) {
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if a.dbError(w, rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)) {
			return
		}
		books = append(books, b)
	}
	if a.dbError(w, rows.Err()) {
		return
	}
	respond(w, 200, books)
}

func (a *API) save(w http.ResponseWriter, r *http.Request, id int64) {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	var input *bookInput
	if err := decoder.Decode(&input); err != nil {
		invalidJSON(w, err)
		return
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		invalidJSON(w, err)
		return
	}
	if input == nil {
		fail(w, 400, "body must be a JSON object")
		return
	}
	input.Title = strings.TrimSpace(input.Title)
	input.Author = strings.TrimSpace(input.Author)
	if input.Title == "" || input.Author == "" {
		fail(w, 400, "title and author are required")
		return
	}
	status := http.StatusOK
	if id == 0 {
		result, err := a.db.ExecContext(r.Context(), "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", input.Title, input.Author, input.Year, input.ISBN)
		if a.dbError(w, err) {
			return
		}
		id, err = result.LastInsertId()
		if a.dbError(w, err) {
			return
		}
		status = http.StatusCreated
		w.Header().Set("Location", fmt.Sprintf("/books/%d", id))
	} else {
		result, err := a.db.ExecContext(r.Context(), "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", input.Title, input.Author, input.Year, input.ISBN, id)
		if a.dbError(w, err) {
			return
		}
		n, err := result.RowsAffected()
		if a.dbError(w, err) {
			return
		}
		if n == 0 {
			fail(w, 404, "book not found")
			return
		}
	}
	respond(w, status, Book{id, input.Title, input.Author, input.Year, input.ISBN})
}

func invalidJSON(w http.ResponseWriter, err error) {
	var tooLarge *http.MaxBytesError
	if errors.As(err, &tooLarge) {
		fail(w, 413, "request body exceeds 1 MiB")
		return
	}
	fail(w, 400, "body must contain one valid JSON object with only title, author, year and isbn fields")
}

func run() error {
	path := os.Getenv("DB_PATH")
	if path == "" {
		path = "books.db"
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	db, err := openDB(path)
	if err != nil {
		return err
	}
	defer db.Close()
	server := &http.Server{Addr: addr, Handler: &API{db}, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	done := make(chan error, 1)
	go func() { done <- server.ListenAndServe() }()
	log.Printf("listening on %s", addr)
	select {
	case err := <-done:
		return err
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			_ = server.Close()
			return err
		}
		return nil
	}
}

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}
