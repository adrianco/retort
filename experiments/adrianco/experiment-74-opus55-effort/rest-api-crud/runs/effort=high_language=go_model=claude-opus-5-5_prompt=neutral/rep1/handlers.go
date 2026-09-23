package main

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxBodyBytes    = 1 << 20 // 1 MiB
	maxTitleLength  = 500
	maxAuthorLength = 300
)

// BookInput is the request payload for creating or updating a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

// Server wires HTTP routes to a Store.
type Server struct {
	store Store
	mux   *http.ServeMux
	now   func() time.Time
}

// NewServer builds the HTTP handler for the book API.
func NewServer(store Store) *Server {
	s := &Server{store: store, mux: http.NewServeMux(), now: time.Now}
	s.mux.HandleFunc("GET /health", s.handleHealth)
	s.mux.HandleFunc("POST /books", s.handleCreate)
	s.mux.HandleFunc("GET /books", s.handleList)
	s.mux.HandleFunc("GET /books/{id}", s.handleGet)
	s.mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	s.mux.HandleFunc("DELETE /books/{id}", s.handleDelete)
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		log.Printf("health check failed: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable", "database": "down"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "database": "up"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeAndValidate(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), in.toBook(0))
	if err != nil {
		internalError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeAndValidate(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), in.toBook(id))
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	err := s.store.Delete(r.Context(), id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		internalError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeAndValidate parses the JSON body into a BookInput, normalises it and
// validates it. On failure it writes the error response and returns false.
func (s *Server) decodeAndValidate(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var maxErr *http.MaxBytesError
		switch {
		case errors.As(err, &maxErr):
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		case errors.Is(err, io.EOF):
			writeError(w, http.StatusBadRequest, "request body is required")
		default:
			writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		}
		return in, false
	}
	if dec.More() {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return in, false
	}

	in.normalize()
	if errs := in.validate(s.now().Year()); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":  "validation failed",
			"fields": errs,
		})
		return in, false
	}
	return in, true
}

func (in *BookInput) normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// validate returns a map of field name to error message; empty means valid.
func (in BookInput) validate(currentYear int) map[string]string {
	errs := map[string]string{}
	switch {
	case in.Title == "":
		errs["title"] = "title is required"
	case utf8.RuneCountInString(in.Title) > maxTitleLength:
		errs["title"] = "title must be at most " + strconv.Itoa(maxTitleLength) + " characters"
	}
	switch {
	case in.Author == "":
		errs["author"] = "author is required"
	case utf8.RuneCountInString(in.Author) > maxAuthorLength:
		errs["author"] = "author must be at most " + strconv.Itoa(maxAuthorLength) + " characters"
	}
	if in.Year != nil && (*in.Year < 0 || *in.Year > currentYear+1) {
		errs["year"] = "year must be between 0 and " + strconv.Itoa(currentYear+1)
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		errs["isbn"] = "isbn must be 10 or 13 digits (hyphens and spaces allowed; ISBN-10 may end in X)"
	}
	return errs
}

func (in BookInput) toBook(id int64) Book {
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}

// validISBN checks the shape of an ISBN-10 or ISBN-13. Checksums are not
// verified so that real-world data with minor inconsistencies is accepted.
func validISBN(s string) bool {
	var digits []rune
	for _, c := range s {
		switch {
		case c == '-' || c == ' ':
			continue
		case c >= '0' && c <= '9', c == 'X' || c == 'x':
			digits = append(digits, c)
		default:
			return false
		}
	}
	for i, c := range digits {
		if (c == 'X' || c == 'x') && !(len(digits) == 10 && i == 9) {
			return false
		}
	}
	return len(digits) == 10 || len(digits) == 13
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func internalError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}
