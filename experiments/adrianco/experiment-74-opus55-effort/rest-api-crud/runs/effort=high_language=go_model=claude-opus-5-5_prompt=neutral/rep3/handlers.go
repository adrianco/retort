package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
)

const maxBodyBytes = 1 << 20 // 1 MiB

// bookInput is the request payload for create/update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Server wires HTTP handlers to a Store.
type Server struct {
	store *Store
}

// NewServer returns an http.Handler exposing the book API.
func NewServer(store *Store) http.Handler {
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
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable", "error": "database unreachable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "time": time.Now().UTC().Format(time.RFC3339)})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeAndValidate(w, r)
	if !ok {
		return
	}
	b, err := s.store.Create(r.Context(), in.toBook())
	if err != nil {
		internalError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(r.Context(), id)
	if s.handleStoreErr(w, err) {
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeAndValidate(w, r)
	if !ok {
		return
	}
	b, err := s.store.Update(r.Context(), id, in.toBook())
	if s.handleStoreErr(w, err) {
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if s.handleStoreErr(w, s.store.Delete(r.Context(), id)) {
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// handleStoreErr writes an error response if err is non-nil and reports whether it did.
func (s *Server) handleStoreErr(w http.ResponseWriter, err error) bool {
	switch {
	case err == nil:
		return false
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found", nil)
	default:
		internalError(w, err)
	}
	return true
}

func (in bookInput) toBook() Book {
	return Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}

// validate normalises the input and returns field-level error messages.
func (in *bookInput) validate() map[string]string {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	errs := map[string]string{}
	if in.Title == "" {
		errs["title"] = "title is required"
	} else if len(in.Title) > 500 {
		errs["title"] = "title must be at most 500 characters"
	}
	if in.Author == "" {
		errs["author"] = "author is required"
	} else if len(in.Author) > 300 {
		errs["author"] = "author must be at most 300 characters"
	}
	if in.Year < 0 || in.Year > time.Now().Year()+1 {
		errs["year"] = "year must be between 0 and next year"
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		errs["isbn"] = "isbn must be 10 or 13 digits (hyphens/spaces allowed; ISBN-10 may end in X)"
	}
	return errs
}

// validISBN checks the shape of an ISBN-10 or ISBN-13 (not the checksum).
func validISBN(s string) bool {
	clean := strings.NewReplacer("-", "", " ", "").Replace(s)
	switch len(clean) {
	case 10:
		for i, c := range clean {
			if !(c >= '0' && c <= '9') && !(i == 9 && (c == 'X' || c == 'x')) {
				return false
			}
		}
		return true
	case 13:
		for _, c := range clean {
			if c < '0' || c > '9' {
				return false
			}
		}
		return true
	}
	return false
}

func decodeAndValidate(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error(), nil)
		return in, false
	}
	if err := dec.Decode(&struct{}{}); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object", nil)
		return in, false
	}
	if errs := in.validate(); len(errs) > 0 {
		writeError(w, http.StatusBadRequest, "validation failed", errs)
		return in, false
	}
	return in, true
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer", nil)
		return 0, false
	}
	return id, true
}

type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string, fields map[string]string) {
	writeJSON(w, status, errorResponse{Error: msg, Fields: fields})
}

func internalError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error", nil)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode response: %v", err)
	}
}
