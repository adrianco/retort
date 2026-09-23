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

const maxBodyBytes = 1 << 20

// bookInput is the request payload for create/update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate trims fields and returns per-field error messages.
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
	} else if len(in.Author) > 200 {
		errs["author"] = "author must be at most 200 characters"
	}
	if in.Year < 0 || in.Year > time.Now().Year()+1 {
		errs["year"] = "year must be between 0 and next year"
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		errs["isbn"] = "isbn must contain 10 or 13 digits (hyphens/spaces allowed; ISBN-10 may end in X)"
	}
	return errs
}

func validISBN(s string) bool {
	clean := strings.NewReplacer("-", "", " ", "").Replace(s)
	switch len(clean) {
	case 10:
		for i, r := range clean {
			if !(r >= '0' && r <= '9') && !(i == 9 && (r == 'X' || r == 'x')) {
				return false
			}
		}
		return true
	case 13:
		for _, r := range clean {
			if r < '0' || r > '9' {
				return false
			}
		}
		return true
	}
	return false
}

// Server holds dependencies for the HTTP handlers.
type Server struct {
	store *Store
}

// Routes returns the HTTP handler with all endpoints registered.
func (s *Server) Routes() http.Handler {
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
	if err := s.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeAndValidate(w, r)
	if !ok {
		return
	}
	b := &Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
	if err := s.store.Create(b); err != nil {
		internalError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(strings.TrimSpace(r.URL.Query().Get("author")))
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
	b, err := s.store.Get(id)
	if err != nil {
		storeError(w, err)
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
	b := &Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
	if err := s.store.Update(b); err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
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

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id", nil)
		return 0, false
	}
	return id, true
}

func decodeAndValidate(w http.ResponseWriter, r *http.Request) (*bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error(), nil)
		return nil, false
	}
	if err := dec.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object", nil)
		return nil, false
	}
	if errs := in.validate(); len(errs) > 0 {
		writeError(w, http.StatusUnprocessableEntity, "validation failed", errs)
		return nil, false
	}
	return &in, true
}

func storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found", nil)
		return
	}
	internalError(w, err)
}

func internalError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error", nil)
}

func writeError(w http.ResponseWriter, status int, msg string, fields map[string]string) {
	body := map[string]any{"error": msg}
	if len(fields) > 0 {
		body["fields"] = fields
	}
	writeJSON(w, status, body)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode response: %v", err)
	}
}
