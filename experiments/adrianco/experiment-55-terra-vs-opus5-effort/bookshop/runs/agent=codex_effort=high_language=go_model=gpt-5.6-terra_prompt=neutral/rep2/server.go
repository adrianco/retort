package main

import (
	"database/sql"
	"encoding/json"
	"errors"
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

type Server struct {
	db *sql.DB
}

func NewServer(db *sql.DB) http.Handler {
	s := &Server{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return mux
}

func (s *Server) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	query := "SELECT id, title, author, year, isbn FROM books"
	var args []any
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}
	query += " ORDER BY id"

	rows, err := s.db.Query(query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	defer rows.Close()

	books := make([]Book, 0)
	for rows.Next() {
		book, err := scanBook(rows)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not read books")
			return
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "could not read books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	book, ok := decodeAndValidateBook(w, r)
	if !ok {
		return
	}

	result, err := s.db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	book.ID, err = result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := requestID(w, r)
	if !ok {
		return
	}
	book, err := s.bookByID(id)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := requestID(w, r)
	if !ok {
		return
	}
	book, ok := decodeAndValidateBook(w, r)
	if !ok {
		return
	}

	result, err := s.db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	affected, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	if affected == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	book.ID = id
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := requestID(w, r)
	if !ok {
		return
	}
	result, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	affected, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	if affected == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) bookByID(id int64) (Book, error) {
	row := s.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
	return scanBook(row)
}

type scanner interface {
	Scan(...any) error
}

func scanBook(s scanner) (Book, error) {
	var book Book
	err := s.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	return book, err
}

func requestID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return 0, false
	}
	return id, true
}

func decodeAndValidateBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	defer r.Body.Close()
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	decoder.DisallowUnknownFields()
	var book Book
	if err := decoder.Decode(&book); err != nil {
		writeError(w, http.StatusBadRequest, "request body must be valid JSON")
		return Book{}, false
	}
	if decoder.Decode(&struct{}{}) != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain one JSON object")
		return Book{}, false
	}
	book.Title = strings.TrimSpace(book.Title)
	book.Author = strings.TrimSpace(book.Author)
	book.ISBN = strings.TrimSpace(book.ISBN)
	if book.Title == "" || book.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return Book{}, false
	}
	return book, true
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
