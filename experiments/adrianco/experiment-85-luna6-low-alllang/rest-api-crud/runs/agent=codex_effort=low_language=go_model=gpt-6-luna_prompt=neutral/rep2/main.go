package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"

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
	if path != ":memory:" {
		if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
			return nil, err
		}
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
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

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			methodNotAllowed(w)
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		switch r.Method {
		case http.MethodPost:
			a.createBook(w, r)
		case http.MethodGet:
			a.listBooks(w, r)
		default:
			methodNotAllowed(w)
		}
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		a.bookByID(w, r, strings.TrimPrefix(r.URL.Path, "/books/"))
		return
	}
	http.NotFound(w, r)
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := decodeBook(r, &b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := validateBook(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	result, err := a.db.Exec(`INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	b.ID, err = result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	var rows *sql.Rows
	var err error
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	if author != "" {
		rows, err = a.db.Query(`SELECT id,title,author,year,isbn FROM books WHERE author = ? ORDER BY id`, author)
	} else {
		rows, err = a.db.Query(`SELECT id,title,author,year,isbn FROM books ORDER BY id`)
	}
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

func (a *API) bookByID(w http.ResponseWriter, r *http.Request, rawID string) {
	if strings.Contains(rawID, "/") || rawID == "" {
		http.NotFound(w, r)
		return
	}
	id, err := strconv.ParseInt(rawID, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := a.getBook(id)
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
		if err := decodeBook(r, &b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		if err := validateBook(b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		result, err := a.db.Exec(`UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, b.Title, b.Author, b.Year, b.ISBN, id)
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
		result, err := a.db.Exec(`DELETE FROM books WHERE id=?`, id)
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
	default:
		methodNotAllowed(w)
	}
}

func (a *API) getBook(id int64) (Book, error) {
	var b Book
	err := a.db.QueryRow(`SELECT id,title,author,year,isbn FROM books WHERE id=?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func decodeBook(r *http.Request, b *Book) error {
	defer r.Body.Close()
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(b); err != nil {
		return fmt.Errorf("invalid JSON body")
	}
	var extra any
	if err := dec.Decode(&extra); err == nil {
		return fmt.Errorf("request must contain one JSON object")
	}
	return nil
}

func validateBook(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func methodNotAllowed(w http.ResponseWriter) {
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func main() {
	dbPath := os.Getenv("BOOKS_DB")
	if dbPath == "" {
		dbPath = "books.db"
	}
	db, err := openDB(dbPath)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("book API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, &API{db: db}))
}
