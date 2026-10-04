package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
)

const maxBodyBytes = 1 << 20

// NewServer wires the HTTP routes to the store.
func NewServer(store *Store) http.Handler {
	s := &server{store: store}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return mux
}

type server struct {
	store *Store
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	if err := s.store.Create(&b); err != nil {
		internalError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(id)
	if err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b.ID = id
	if err := s.store.Update(b); err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(id); err != nil {
		storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBook reads and validates a book from the request body, writing the
// error response itself when it returns false.
func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var in struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return Book{}, false
	}
	b := Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}
	var problems []string
	if b.Title == "" {
		problems = append(problems, "title is required")
	}
	if b.Author == "" {
		problems = append(problems, "author is required")
	}
	if b.Year < 0 {
		problems = append(problems, "year must not be negative")
	}
	if len(problems) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":   "validation failed",
			"details": problems,
		})
		return Book{}, false
	}
	return b, true
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	internalError(w, err)
}

func internalError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}
