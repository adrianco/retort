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

// Book is a record in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type Server struct{ db *sql.DB }

func NewServer(db *sql.DB) (*Server, error) {
	if db == nil {
		return nil, errors.New("database is required")
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`); err != nil {
		return nil, fmt.Errorf("create books table: %w", err)
	}
	return &Server{db: db}, nil
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			methodNotAllowed(w)
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		s.books(w, r)
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		idText := strings.TrimPrefix(r.URL.Path, "/books/")
		if idText == "" || strings.Contains(idText, "/") {
			notFound(w)
			return
		}
		id, err := strconv.ParseInt(idText, 10, 64)
		if err != nil || id < 1 {
			writeError(w, http.StatusBadRequest, "invalid book id")
			return
		}
		s.book(w, r, id)
		return
	}
	notFound(w)
}

func (s *Server) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		book, ok := decodeBook(w, r)
		if !ok {
			return
		}
		result, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`, book.Title, book.Author, book.Year, book.ISBN)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		book.ID, _ = result.LastInsertId()
		w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
		writeJSON(w, http.StatusCreated, book)
	case http.MethodGet:
		author := r.URL.Query().Get("author")
		query, args := `SELECT id, title, author, year, isbn FROM books`, []any{}
		if author != "" {
			query += ` WHERE author = ?`
			args = append(args, author)
		}
		query += ` ORDER BY id`
		rows, err := s.db.Query(query, args...)
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
	default:
		methodNotAllowed(w)
	}
}

func (s *Server) book(w http.ResponseWriter, r *http.Request, id int64) {
	switch r.Method {
	case http.MethodGet:
		book, err := s.find(id)
		if errors.Is(err, sql.ErrNoRows) {
			notFound(w)
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not get book")
			return
		}
		writeJSON(w, http.StatusOK, book)
	case http.MethodPut:
		book, ok := decodeBook(w, r)
		if !ok {
			return
		}
		result, err := s.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`, book.Title, book.Author, book.Year, book.ISBN, id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not update book")
			return
		}
		changed, _ := result.RowsAffected()
		if changed == 0 {
			notFound(w)
			return
		}
		book.ID = id
		writeJSON(w, http.StatusOK, book)
	case http.MethodDelete:
		result, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not delete book")
			return
		}
		changed, _ := result.RowsAffected()
		if changed == 0 {
			notFound(w)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		methodNotAllowed(w)
	}
}

func (s *Server) find(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	defer r.Body.Close()
	var b Book
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return Book{}, false
	}
	if decoder.Decode(&struct{}{}) != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain one JSON object")
		return Book{}, false
	}
	b.Title, b.Author = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return Book{}, false
	}
	return b, true
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func notFound(w http.ResponseWriter) { writeError(w, http.StatusNotFound, "not found") }
func methodNotAllowed(w http.ResponseWriter) {
	w.Header().Set("Allow", "GET, POST, PUT, DELETE")
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func main() {
	dbPath := os.Getenv("BOOKS_DB")
	if dbPath == "" {
		dbPath = "books.db"
	}
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	server, err := NewServer(db)
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("book API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, server))
}
