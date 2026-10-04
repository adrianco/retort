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

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type Server struct{ db *sql.DB }

func NewServer(db *sql.DB) (*Server, error) {
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`); err != nil {
		return nil, fmt.Errorf("create books table: %w", err)
	}
	s := &Server{db: db}
	return s, nil
}

func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return mux
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if !decodeBook(w, r, &b) {
		return
	}
	if err := validateBook(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	result, err := s.db.Exec(`INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN)
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

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	var rows *sql.Rows
	var err error
	if author := strings.TrimSpace(r.URL.Query().Get("author")); author != "" {
		rows, err = s.db.Query(`SELECT id,title,author,year,isbn FROM books WHERE author = ? ORDER BY id`, author)
	} else {
		rows, err = s.db.Query(`SELECT id,title,author,year,isbn FROM books ORDER BY id`)
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

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	b, err := s.findBook(id)
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

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	var b Book
	if !decodeBook(w, r, &b) {
		return
	}
	if err := validateBook(b); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	res, err := s.db.Exec(`UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, b.ISBN, id)
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
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`DELETE FROM books WHERE id=?`, id)
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

func (s *Server) findBook(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id,title,author,year,isbn FROM books WHERE id=?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}
func bookID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}
func validateBook(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return errors.New("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return errors.New("author is required")
	}
	return nil
}
func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	var extra any
	if err := dec.Decode(&extra); err == nil {
		writeError(w, http.StatusBadRequest, "request body must contain one JSON object")
		return false
	} else if !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	return true
}
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func main() {
	path := os.Getenv("BOOKS_DB")
	if path == "" {
		path = "books.db"
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	if err := db.Ping(); err != nil {
		log.Fatal(err)
	}
	s, err := NewServer(db)
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("book API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, s.Routes()))
}
