package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// maxBodyBytes caps request bodies to protect the server from oversized payloads.
const maxBodyBytes = 1 << 20 // 1 MiB

// FieldError describes a single validation failure.
type FieldError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

// bookInput is the request body for create and update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate returns the list of field errors; an empty slice means valid.
func (in bookInput) Validate() []FieldError {
	var errs []FieldError
	if strings.TrimSpace(in.Title) == "" {
		errs = append(errs, FieldError{"title", "title is required"})
	}
	if strings.TrimSpace(in.Author) == "" {
		errs = append(errs, FieldError{"author", "author is required"})
	}
	maxYear := time.Now().Year() + 1
	if in.Year < 0 || in.Year > maxYear {
		errs = append(errs, FieldError{"year", "year must be between 0 and " + strconv.Itoa(maxYear)})
	}
	return errs
}

// Server wires HTTP routes to the store.
type Server struct {
	store *Store
	mux   *http.ServeMux
}

// NewServer builds an HTTP handler backed by store.
func NewServer(store *Store) *Server {
	s := &Server{store: store, mux: http.NewServeMux()}
	s.mux.HandleFunc("GET /health", s.health)
	s.mux.HandleFunc("POST /books", s.createBook)
	s.mux.HandleFunc("GET /books", s.listBooks)
	s.mux.HandleFunc("GET /books/{id}", s.getBook)
	s.mux.HandleFunc("PUT /books/{id}", s.updateBook)
	s.mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return s
}

// ServeHTTP implements http.Handler.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable", "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(in.toBook(0))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.URL.Query().Get("author"))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(id)
	if err != nil {
		writeStoreError(w, err, "failed to get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(in.toBook(id))
	if err != nil {
		writeStoreError(w, err, "failed to update book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(id); err != nil {
		writeStoreError(w, err, "failed to delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (in bookInput) toBook(id int64) Book {
	return Book{
		ID:     id,
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}
}

// decodeBookInput parses and validates a JSON book body, writing the error
// response itself and returning false on failure.
func decodeBookInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		} else {
			writeError(w, http.StatusBadRequest, "invalid JSON body")
		}
		return bookInput{}, false
	}
	if errs := in.Validate(); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":  "validation failed",
			"fields": errs,
		})
		return bookInput{}, false
	}
	return in, true
}

// parseID reads the {id} path value, writing a 400 response on failure.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func writeStoreError(w http.ResponseWriter, err error, fallback string) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeError(w, http.StatusInternalServerError, fallback)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
