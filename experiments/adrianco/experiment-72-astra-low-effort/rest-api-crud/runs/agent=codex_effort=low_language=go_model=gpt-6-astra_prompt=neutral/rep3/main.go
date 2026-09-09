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

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func fail(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func allowed(w http.ResponseWriter, methods string) {
	w.Header().Set("Allow", methods)
	fail(w, http.StatusMethodNotAllowed, "method not allowed")
}
func input(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var b Book
	// Decode into input-only fields, so clients cannot set the database ID.
	var in struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	err := d.Decode(&in)
	if err == nil {
		var extra any
		if d.Decode(&extra) != io.EOF {
			err = errors.New("extra JSON")
		}
	}
	if err != nil {
		fail(w, 400, "body must be one valid JSON object with title, author, year and isbn fields")
		return b, false
	}
	b = Book{Title: strings.TrimSpace(in.Title), Author: strings.TrimSpace(in.Author), Year: in.Year, ISBN: in.ISBN}
	if b.Title == "" || b.Author == "" {
		fail(w, 400, "title and author are required")
		return b, false
	}
	return b, true
}
func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			allowed(w, "GET")
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
		case http.MethodPost:
			b, ok := input(w, r)
			if !ok {
				return
			}
			result, err := a.db.ExecContext(r.Context(), "INSERT INTO books(title, author, year, isbn) VALUES(?,?,?,?)", b.Title, b.Author, b.Year, b.ISBN)
			if err != nil {
				fail(w, 500, "database operation failed")
				return
			}
			b.ID, err = result.LastInsertId()
			if err != nil {
				fail(w, 500, "database operation failed")
				return
			}
			w.Header().Set("Location", fmt.Sprintf("/books/%d", b.ID))
			writeJSON(w, 201, b)
		case http.MethodGet:
			query := "SELECT id,title,author,year,isbn FROM books"
			args := []any{}
			if r.URL.Query().Has("author") {
				query += " WHERE author = ?"
				args = append(args, r.URL.Query().Get("author"))
			}
			rows, err := a.db.QueryContext(r.Context(), query+" ORDER BY id", args...)
			if err != nil {
				fail(w, 500, "database operation failed")
				return
			}
			defer rows.Close()
			books := []Book{}
			for rows.Next() {
				var b Book
				if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
					fail(w, 500, "database operation failed")
					return
				}
				books = append(books, b)
			}
			if rows.Err() != nil {
				fail(w, 500, "database operation failed")
				return
			}
			writeJSON(w, 200, books)
		default:
			allowed(w, "GET, POST")
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
			fail(w, 500, "database operation failed")
			return
		}
		writeJSON(w, 200, b)
	case http.MethodPut, http.MethodDelete:
		var result sql.Result
		var b Book
		if r.Method == http.MethodPut {
			var ok bool
			b, ok = input(w, r)
			if !ok {
				return
			}
			b.ID = id
			result, err = a.db.ExecContext(r.Context(), "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?", b.Title, b.Author, b.Year, b.ISBN, id)
		} else {
			result, err = a.db.ExecContext(r.Context(), "DELETE FROM books WHERE id=?", id)
		}
		if err != nil {
			fail(w, 500, "database operation failed")
			return
		}
		n, err := result.RowsAffected()
		if err != nil {
			fail(w, 500, "database operation failed")
			return
		}
		if n == 0 {
			fail(w, 404, "book not found")
			return
		}
		if r.Method == http.MethodDelete {
			w.WriteHeader(http.StatusNoContent)
		} else {
			writeJSON(w, 200, b)
		}
	default:
		allowed(w, "GET, PUT, DELETE")
	}
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
	server := &http.Server{Addr: addr, Handler: &API{db: db}, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	log.Printf("book API listening on %s", addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
