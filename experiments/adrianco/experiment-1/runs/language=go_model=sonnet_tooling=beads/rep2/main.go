package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type server struct {
	db *sql.DB
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (s *server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.listBooks(w, r)
	case http.MethodPost:
		s.createBook(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) handleBook(w http.ResponseWriter, r *http.Request) {
	// Path: /books/{id}
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	switch r.Method {
	case http.MethodGet:
		s.getBook(w, r, id)
	case http.MethodPut:
		s.updateBook(w, r, id)
	case http.MethodDelete:
		s.deleteBook(w, r, id)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return
	}
	if err := dbCreateBook(s.db, &b); err != nil {
		log.Printf("createBook: %v", err)
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := dbListBooks(s.db, author)
	if err != nil {
		log.Printf("listBooks: %v", err)
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	if books == nil {
		books = []Book{}
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	b, err := dbGetBook(s.db, id)
	if err == sql.ErrNoRows {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		log.Printf("getBook: %v", err)
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return
	}
	if err := dbUpdateBook(s.db, id, &b); err == sql.ErrNoRows {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		log.Printf("updateBook: %v", err)
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	if err := dbDeleteBook(s.db, id); err == sql.ErrNoRows {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		log.Printf("deleteBook: %v", err)
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func newMux(db *sql.DB) http.Handler {
	s := &server{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", s.handleHealth)
	mux.HandleFunc("/books", s.handleBooks)
	mux.HandleFunc("/books/", s.handleBook)
	return mux
}

func main() {
	db, err := initDB("books.db")
	if err != nil {
		log.Fatalf("init db: %v", err)
	}
	defer db.Close()

	addr := ":8080"
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, newMux(db)); err != nil {
		log.Fatalf("server: %v", err)
	}
}
