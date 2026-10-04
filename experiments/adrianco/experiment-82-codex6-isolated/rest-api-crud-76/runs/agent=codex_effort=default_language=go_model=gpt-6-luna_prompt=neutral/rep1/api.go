package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type api struct{ db *sql.DB }

func initialize(db *sql.DB) error {
	_, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`)
	return err
}

func newAPI(db *sql.DB) http.Handler {
	a := &api{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
	return mux
}

func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if !decodeBook(w, r, &b) {
		return
	}
	if err := validate(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	res, err := a.db.Exec(`INSERT INTO books(title, author, year, isbn) VALUES(?, ?, ?, ?)`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, strings.TrimSpace(b.ISBN))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	b.ID, err = res.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	query := `SELECT id, title, author, year, isbn FROM books`
	args := []any{}
	if author := strings.TrimSpace(r.URL.Query().Get("author")); author != "" {
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

func (a *api) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	b, err := a.findBook(id)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	var b Book
	if !decodeBook(w, r, &b) {
		return
	}
	if err := validate(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	res, err := a.db.Exec(`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, strings.TrimSpace(b.ISBN), id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	n, err := res.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, http.StatusOK, b)
}

func (a *api) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	res, err := a.db.Exec(`DELETE FROM books WHERE id=?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	n, err := res.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (a *api) findBook(id int64) (Book, error) {
	var b Book
	err := a.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id=?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) bool {
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request must contain one JSON object")
		return false
	}
	return true
}

func validate(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

func bookID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
