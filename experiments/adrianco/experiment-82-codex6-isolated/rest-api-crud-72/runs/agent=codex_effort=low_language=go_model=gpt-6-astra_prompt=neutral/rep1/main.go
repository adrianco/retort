package main

import (
	"database/sql"
	"encoding/json"
	"errors"
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

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func fail(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func methodError(w http.ResponseWriter, allow string) {
	w.Header().Set("Allow", allow)
	fail(w, http.StatusMethodNotAllowed, "method not allowed")
}

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			methodError(w, "GET")
			return
		}
		if err := a.db.PingContext(r.Context()); err != nil {
			fail(w, 503, "database unavailable")
			return
		}
		writeJSON(w, 200, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		switch r.Method {
		case http.MethodGet:
			a.list(w, r)
		case http.MethodPost:
			a.save(w, r, 0)
		default:
			methodError(w, "GET, POST")
		}
		return
	}
	if !strings.HasPrefix(r.URL.Path, "/books/") || strings.Contains(strings.TrimPrefix(r.URL.Path, "/books/"), "/") {
		fail(w, 404, "not found")
		return
	}
	id, err := strconv.ParseInt(strings.TrimPrefix(r.URL.Path, "/books/"), 10, 64)
	if err != nil || id <= 0 {
		fail(w, 400, "id must be a positive integer")
		return
	}
	switch r.Method {
	case http.MethodGet:
		var b Book
		err := a.db.QueryRowContext(r.Context(), "SELECT id,title,author,year,isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
		if errors.Is(err, sql.ErrNoRows) {
			fail(w, 404, "book not found")
			return
		}
		if err != nil {
			fail(w, 500, "database error")
			return
		}
		writeJSON(w, 200, b)
	case http.MethodPut:
		a.save(w, r, id)
	case http.MethodDelete:
		result, err := a.db.ExecContext(r.Context(), "DELETE FROM books WHERE id = ?", id)
		if err != nil {
			fail(w, 500, "database error")
			return
		}
		n, err := result.RowsAffected()
		if err != nil {
			fail(w, 500, "database error")
			return
		}
		if n == 0 {
			fail(w, 404, "book not found")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		methodError(w, "GET, PUT, DELETE")
	}
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
		fail(w, 500, "database error")
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			fail(w, 500, "database error")
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		fail(w, 500, "database error")
		return
	}
	writeJSON(w, 200, books)
}

func (a *API) save(w http.ResponseWriter, r *http.Request, id int64) {
	var input struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&input); err != nil {
		bodyError(w, err)
		return
	}
	if err := dec.Decode(new(any)); err != io.EOF {
		bodyError(w, err)
		return
	}
	input.Title = strings.TrimSpace(input.Title)
	input.Author = strings.TrimSpace(input.Author)
	if input.Title == "" || input.Author == "" {
		fail(w, 400, "title and author are required")
		return
	}
	b := Book{id, input.Title, input.Author, input.Year, input.ISBN}
	status := http.StatusOK
	if id == 0 {
		result, err := a.db.ExecContext(r.Context(), "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", b.Title, b.Author, b.Year, b.ISBN)
		if err != nil {
			fail(w, 500, "database error")
			return
		}
		b.ID, err = result.LastInsertId()
		if err != nil {
			fail(w, 500, "database error")
			return
		}
		status = http.StatusCreated
		w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	} else {
		result, err := a.db.ExecContext(r.Context(), "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?", b.Title, b.Author, b.Year, b.ISBN, id)
		if err != nil {
			fail(w, 500, "database error")
			return
		}
		n, err := result.RowsAffected()
		if err != nil {
			fail(w, 500, "database error")
			return
		}
		if n == 0 {
			fail(w, 404, "book not found")
			return
		}
	}
	writeJSON(w, status, b)
}

func bodyError(w http.ResponseWriter, err error) {
	var tooLarge *http.MaxBytesError
	if errors.As(err, &tooLarge) {
		fail(w, 413, "request body exceeds 1 MiB")
		return
	}
	fail(w, 400, "body must be a single JSON object with title, author, year and isbn fields")
}

func main() {
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
		log.Fatal(err)
	}
	defer db.Close()
	server := &http.Server{Addr: addr, Handler: &API{db}, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	log.Printf("listening on %s", addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Print(err)
	}
}
