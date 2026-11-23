package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Details struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}
type Book struct {
	ID int64 `json:"id"`
	Details
}

func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	_, err = db.Exec("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT NOT NULL)")
	if err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
func problem(w http.ResponseWriter, status int, msg string) {
	respond(w, status, map[string]string{"error": msg})
}

type api struct{ db *sql.DB }

func (a api) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	var allow string
	var err error
	switch {
	case r.URL.Path == "/health":
		allow = "GET"
		if r.Method == "GET" {
			if a.db.PingContext(r.Context()) != nil {
				problem(w, 503, "database unavailable")
			} else {
				respond(w, 200, map[string]string{"status": "ok"})
			}
			return
		}
	case r.URL.Path == "/books":
		allow = "GET, POST"
		switch r.Method {
		case "GET":
			err = a.list(w, r)
		case "POST":
			err = a.save(w, r, 0)
		}
	case strings.HasPrefix(r.URL.Path, "/books/"):
		id, e := strconv.ParseInt(strings.TrimPrefix(r.URL.Path, "/books/"), 10, 64)
		if e != nil || id < 1 {
			problem(w, 404, "book not found")
			return
		}
		allow = "GET, PUT, DELETE"
		switch r.Method {
		case "GET":
			var b Book
			err = a.db.QueryRowContext(r.Context(), "SELECT id,title,author,year,isbn FROM books WHERE id=?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
			if err == nil {
				respond(w, 200, b)
			}
		case "PUT":
			err = a.save(w, r, id)
		case "DELETE":
			var deleted int64
			err = a.db.QueryRowContext(r.Context(), "DELETE FROM books WHERE id=? RETURNING id", id).Scan(&deleted)
			if err == nil {
				w.WriteHeader(http.StatusNoContent)
			}
		}
	default:
		problem(w, 404, "route not found")
		return
	}
	if errors.Is(err, sql.ErrNoRows) {
		problem(w, 404, "book not found")
		return
	}
	if err != nil {
		log.Print(err)
		problem(w, 500, "database error")
		return
	}
	for _, method := range strings.Split(allow, ", ") {
		if r.Method == method {
			return
		}
	}
	w.Header().Set("Allow", allow)
	problem(w, 405, "method not allowed")
}

func (a api) list(w http.ResponseWriter, r *http.Request) error {
	query := "SELECT id,title,author,year,isbn FROM books"
	var args []any
	if r.URL.Query().Has("author") {
		query += " WHERE author=?"
		args = append(args, r.URL.Query().Get("author"))
	}
	rows, err := a.db.QueryContext(r.Context(), query+" ORDER BY id", args...)
	if err != nil {
		return err
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return err
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return err
	}
	respond(w, 200, books)
	return nil
}

func (a api) save(w http.ResponseWriter, r *http.Request, id int64) error {
	var b Book
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if dec.Decode(&b.Details) != nil || dec.Decode(new(any)) != io.EOF {
		problem(w, 400, "expected one book JSON object")
		return nil
	}
	b.Author = strings.TrimSpace(b.Author)
	b.Title = strings.TrimSpace(b.Title)
	if b.Title == "" || b.Author == "" {
		problem(w, 400, "title and author are required")
		return nil
	}
	args := []any{b.Title, b.Author, b.Year, b.ISBN}
	query := "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?) RETURNING id"
	status := 201
	if id != 0 {
		query = "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=? RETURNING id"
		args = append(args, id)
		status = 200
	}
	if err := a.db.QueryRowContext(r.Context(), query, args...).Scan(&b.ID); err != nil {
		return err
	}
	if status == 201 {
		w.Header().Set("Location", fmt.Sprintf("/books/%d", b.ID))
	}
	respond(w, status, b)
	return nil
}

func main() {
	addr := flag.String("addr", ":8080", "listen address")
	path := flag.String("db", "books.db", "SQLite database path")
	flag.Parse()
	db, err := openDB(*path)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	server := http.Server{Addr: *addr, Handler: api{db}, ReadHeaderTimeout: 5 * time.Second}
	log.Fatal(server.ListenAndServe())
}
