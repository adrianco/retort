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

// bookInput is the request body for creating or updating a book.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate normalizes the input and returns a map of field name to problem,
// empty when the input is valid.
func (in *bookInput) validate() map[string]string {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	problems := map[string]string{}
	if in.Title == "" {
		problems["title"] = "title is required"
	}
	if in.Author == "" {
		problems["author"] = "author is required"
	}
	if in.Year < 0 {
		problems["year"] = "year must not be negative"
	}
	return problems
}

// Server exposes the book collection over HTTP.
type Server struct {
	store *Store
}

// NewHandler returns the HTTP handler for the API backed by store.
func NewHandler(store *Store) http.Handler {
	s := &Server{store: store}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return mux
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
	if err != nil {
		writeStoreError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		writeStoreError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// parseID extracts the {id} path value, writing a 400 response if it is not a
// positive integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

// decodeBook reads and validates a book from the request body, writing the
// error response itself when the body is malformed or invalid.
func decodeBook(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
			return in, false
		}
		writeError(w, http.StatusBadRequest, "request body must be a valid JSON book object")
		return in, false
	}
	if problems := in.validate(); len(problems) > 0 {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]any{
			"error":  "validation failed",
			"fields": problems,
		})
		return in, false
	}
	return in, true
}

func writeStoreError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	log.Printf("store error: %v", err)
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
