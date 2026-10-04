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

type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type API struct{ db *sql.DB }

func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
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
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		if err := a.db.PingContext(ctx); err != nil {
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

func (a *API) databaseError(w http.ResponseWriter, err error) {
	log.Printf("database error: %v", err)
	fail(w, 500, "internal server error")
}

func (a *API) list(w http.ResponseWriter, r *http.Request) {
	query := "SELECT id,title,author,year,isbn FROM books"
	args := []any{}
	if r.URL.Query().Has("author") {
		query += " WHERE author = ?"
		args = append(args, r.URL.Query().Get("author"))
	}
	rows, err := a.db.QueryContext(r.Context(), query+" ORDER BY id", args...)
	if err != nil {
		a.databaseError(w, err)
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			a.databaseError(w, err)
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		a.databaseError(w, err)
		return
	}
	respond(w, 200, books)
}

func (a *API) get(w http.ResponseWriter, r *http.Request, id int64) {
	var b Book
	err := a.db.QueryRowContext(r.Context(), "SELECT id,title,author,year,isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		fail(w, 404, "book not found")
		return
	}
	if err != nil {
		a.databaseError(w, err)
		return
	}
	respond(w, 200, b)
}

func (a *API) save(w http.ResponseWriter, r *http.Request, id int64) {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var input *bookInput
	err := dec.Decode(&input)
	if err == nil {
		var extra any
		if e := dec.Decode(&extra); e != io.EOF {
			if e != nil {
				err = e
			} else {
				err = errors.New("expected one JSON object")
			}
		}
	}
	if err != nil {
		var sizeErr *http.MaxBytesError
		if errors.As(err, &sizeErr) {
			fail(w, 413, "request body too large")
			return
		}
		fail(w, 400, "body must be a single JSON object with title, author, year, and isbn fields")
		return
	}
	if input == nil || strings.TrimSpace(input.Title) == "" || strings.TrimSpace(input.Author) == "" {
		fail(w, 400, "title and author are required")
		return
	}
	input.Title = strings.TrimSpace(input.Title)
	input.Author = strings.TrimSpace(input.Author)
	status := http.StatusOK
	if id == 0 {
		result, err := a.db.ExecContext(r.Context(), "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", input.Title, input.Author, input.Year, input.ISBN)
		if err != nil {
			a.databaseError(w, err)
			return
		}
		id, err = result.LastInsertId()
		if err != nil {
			a.databaseError(w, err)
			return
		}
		w.Header().Set("Location", fmt.Sprintf("/books/%d", id))
		status = http.StatusCreated
	} else {
		result, err := a.db.ExecContext(r.Context(), "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?", input.Title, input.Author, input.Year, input.ISBN, id)
		if err != nil {
			a.databaseError(w, err)
			return
		}
		n, err := result.RowsAffected()
		if err != nil {
			a.databaseError(w, err)
			return
		}
		if n == 0 {
			fail(w, 404, "book not found")
			return
		}
	}
	respond(w, status, Book{ID: id, Title: input.Title, Author: input.Author, Year: input.Year, ISBN: input.ISBN})
}

func (a *API) delete(w http.ResponseWriter, r *http.Request, id int64) {
	result, err := a.db.ExecContext(r.Context(), "DELETE FROM books WHERE id=?", id)
	if err != nil {
		a.databaseError(w, err)
		return
	}
	n, err := result.RowsAffected()
	if err != nil {
		a.databaseError(w, err)
		return
	}
	if n == 0 {
		fail(w, 404, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
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
	server := &http.Server{Addr: addr, Handler: newHandler(db), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	log.Printf("listening on %s", addr)
	return server.ListenAndServe()
}
func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}
