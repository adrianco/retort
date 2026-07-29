package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
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

type Server struct {
	db *sql.DB
}

func main() {
	databasePath := os.Getenv("DATABASE_PATH")
	if databasePath == "" {
		databasePath = "books.db"
	}
	db, err := sql.Open("sqlite", databasePath)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	server, err := NewServer(db)
	if err != nil {
		log.Fatal(err)
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("book API listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, server))
}

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
			methodNotAllowed(w, http.MethodGet)
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
		s.book(w, r)
		return
	}
	writeError(w, http.StatusNotFound, "not found")
}

func (s *Server) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		books, err := s.listBooks(r.URL.Query().Get("author"))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		writeJSON(w, http.StatusOK, books)
	case http.MethodPost:
		var input Book
		if !decodeJSON(w, r, &input) {
			return
		}
		if !validateBook(input) {
			writeError(w, http.StatusBadRequest, "title and author are required")
			return
		}
		result, err := s.db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", input.Title, input.Author, input.Year, input.ISBN)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		input.ID, _ = result.LastInsertId()
		writeJSON(w, http.StatusCreated, input)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPost)
	}
}

func (s *Server) book(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(strings.TrimPrefix(r.URL.Path, "/books/"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		book, err := s.findBook(id)
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not get book")
			return
		}
		writeJSON(w, http.StatusOK, book)
	case http.MethodPut:
		var input Book
		if !decodeJSON(w, r, &input) {
			return
		}
		if !validateBook(input) {
			writeError(w, http.StatusBadRequest, "title and author are required")
			return
		}
		result, err := s.db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", input.Title, input.Author, input.Year, input.ISBN, id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not update book")
			return
		}
		if n, _ := result.RowsAffected(); n == 0 {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		input.ID = id
		writeJSON(w, http.StatusOK, input)
	case http.MethodDelete:
		result, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not delete book")
			return
		}
		if n, _ := result.RowsAffected(); n == 0 {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPut, http.MethodDelete)
	}
}

func validateBook(book Book) bool {
	return strings.TrimSpace(book.Title) != "" && strings.TrimSpace(book.Author) != ""
}

func (s *Server) listBooks(author string) ([]Book, error) {
	query := "SELECT id, title, author, year, isbn FROM books"
	args := []any{}
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}
	query += " ORDER BY id"
	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	books := make([]Book, 0)
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

func (s *Server) findBook(id int64) (Book, error) {
	var book Book
	err := s.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	return book, err
}

func decodeJSON(w http.ResponseWriter, r *http.Request, destination any) bool {
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(destination); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func methodNotAllowed(w http.ResponseWriter, methods ...string) {
	w.Header().Set("Allow", strings.Join(methods, ", "))
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}
