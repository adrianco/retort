package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"flag"
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

func newHandler(db *sql.DB) http.Handler { return &API{db: db} }

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
func methodNotAllowed(w http.ResponseWriter, allow string) {
	w.Header().Set("Allow", allow)
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
	if strings.HasPrefix(r.URL.Path, "/books/") {
		raw := strings.TrimPrefix(r.URL.Path, "/books/")
		if raw == "" || strings.Contains(raw, "/") {
			fail(w, 404, "not found")
			return
		}
		id, err := strconv.ParseInt(raw, 10, 64)
		if err != nil || id <= 0 {
			fail(w, 400, "id must be a positive integer")
			return
		}
		switch r.Method {
		case http.MethodGet:
			a.get(w, r, id)
		case http.MethodPut:
			a.save(w, r, id)
		case http.MethodDelete:
			a.delete(w, r, id)
		default:
			methodNotAllowed(w, "GET, PUT, DELETE")
		}
		return
	}
	fail(w, 404, "not found")
}

func decodeInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var input bookInput
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	err := dec.Decode(&input)
	if err == nil {
		var extra any
		if dec.Decode(&extra) != io.EOF {
			err = errors.New("extra JSON")
		}
	}
	if err != nil {
		fail(w, 400, "body must be a single JSON object with title, author, year and isbn fields")
		return input, false
	}
	input.Title = strings.TrimSpace(input.Title)
	input.Author = strings.TrimSpace(input.Author)
	if input.Title == "" || input.Author == "" {
		fail(w, 400, "title and author are required")
		return input, false
	}
	return input, true
}

func (a *API) save(w http.ResponseWriter, r *http.Request, id int64) {
	input, ok := decodeInput(w, r)
	if !ok {
		return
	}
	var result sql.Result
	var err error
	if id == 0 {
		result, err = a.db.ExecContext(r.Context(), "INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)", input.Title, input.Author, input.Year, input.ISBN)
	} else {
		result, err = a.db.ExecContext(r.Context(), "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?", input.Title, input.Author, input.Year, input.ISBN, id)
	}
	if err != nil {
		fail(w, 500, "could not save book")
		return
	}
	status := http.StatusOK
	if id == 0 {
		id, err = result.LastInsertId()
		status = http.StatusCreated
	} else {
		var count int64
		count, err = result.RowsAffected()
		if err == nil && count == 0 {
			fail(w, 404, "book not found")
			return
		}
	}
	if err != nil {
		fail(w, 500, "could not save book")
		return
	}
	if status == http.StatusCreated {
		w.Header().Set("Location", fmt.Sprintf("/books/%d", id))
	}
	respond(w, status, Book{id, input.Title, input.Author, input.Year, input.ISBN})
}

func (a *API) list(w http.ResponseWriter, r *http.Request) {
	query := "SELECT id, title, author, year, isbn FROM books"
	var args []any
	if r.URL.Query().Has("author") {
		query += " WHERE author = ?"
		args = append(args, r.URL.Query().Get("author"))
	}
	query += " ORDER BY id"
	rows, err := a.db.QueryContext(r.Context(), query, args...)
	if err != nil {
		fail(w, 500, "could not list books")
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			fail(w, 500, "could not read books")
			return
		}
		books = append(books, book)
	}
	if rows.Err() != nil {
		fail(w, 500, "could not read books")
		return
	}
	respond(w, 200, books)
}
func (a *API) get(w http.ResponseWriter, r *http.Request, id int64) {
	var book Book
	err := a.db.QueryRowContext(r.Context(), "SELECT id, title, author, year, isbn FROM books WHERE id=?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		fail(w, 404, "book not found")
		return
	}
	if err != nil {
		fail(w, 500, "could not read book")
		return
	}
	respond(w, 200, book)
}
func (a *API) delete(w http.ResponseWriter, r *http.Request, id int64) {
	result, err := a.db.ExecContext(r.Context(), "DELETE FROM books WHERE id=?", id)
	if err != nil {
		fail(w, 500, "could not delete book")
		return
	}
	count, err := result.RowsAffected()
	if err != nil {
		fail(w, 500, "could not delete book")
		return
	}
	if count == 0 {
		fail(w, 404, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	path := flag.String("db", "books.db", "SQLite database path")
	flag.Parse()
	db, err := openDB(*path)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	server := &http.Server{Addr: *addr, Handler: newHandler(db), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	done := make(chan struct{})
	go func() {
		defer close(done)
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("shutdown: %v", err)
			_ = server.Close()
		}
	}()
	log.Printf("listening on %s", *addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Printf("server: %v", err)
	}
	stop()
	<-done
}
