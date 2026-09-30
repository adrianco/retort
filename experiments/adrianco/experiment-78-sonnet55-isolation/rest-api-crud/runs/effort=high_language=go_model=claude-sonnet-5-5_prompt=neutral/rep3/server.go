package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
)

const maxBodyBytes = 1 << 20

// Server exposes the book store over HTTP.
type Server struct {
	store *Store
}

// NewHandler builds the HTTP handler for the API.
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

// bookInput is the request payload for create and update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate trims fields and returns a map of field errors (empty if valid).
func (in *bookInput) validate() map[string]string {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	errs := map[string]string{}
	if in.Title == "" {
		errs["title"] = "title is required"
	}
	if in.Author == "" {
		errs["author"] = "author is required"
	}
	if in.Year < 0 || in.Year > time.Now().Year()+1 {
		errs["year"] = "year must be between 0 and next year"
	}
	if len(in.ISBN) > 20 {
		errs["isbn"] = "isbn must be at most 20 characters"
	}
	return errs
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unhealthy"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b, err := s.store.Create(Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
	if err != nil {
		serverError(w, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", b.ID))
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		serverError(w, err)
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
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b, err := s.store.Update(id, Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
	if err != nil {
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

// decodeBook parses and validates a JSON body, writing an error response on failure.
func decodeBook(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		var tooBig *http.MaxBytesError
		if errors.As(err, &tooBig) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		} else {
			writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		}
		return in, false
	}
	if _, err := dec.Token(); err != io.EOF {
		writeError(w, http.StatusBadRequest, "invalid JSON body: unexpected trailing data")
		return in, false
	}
	if errs := in.validate(); len(errs) > 0 {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]any{
			"error":  "validation failed",
			"fields": errs,
		})
		return in, false
	}
	return in, true
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
	serverError(w, err)
}

func serverError(w http.ResponseWriter, err error) {
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
