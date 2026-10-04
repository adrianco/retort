package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
)

const maxBodyBytes = 1 << 20

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

type errorResponse struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details,omitempty"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

// writeStoreError maps a store error to a response, hiding internal details.
func writeStoreError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	log.Printf("store error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// bookInput is the request body for create and update. Pointers distinguish
// an omitted field from a zero value.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// decodeBook reads and validates a book from the request body. On failure it
// writes the error response and returns false.
func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var tooLarge *http.MaxBytesError
		var typeErr *json.UnmarshalTypeError
		switch {
		case errors.As(err, &tooLarge):
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		case errors.As(err, &typeErr):
			writeError(w, http.StatusBadRequest, "invalid type for field "+strconv.Quote(typeErr.Field))
		default:
			writeError(w, http.StatusBadRequest, "request body must be valid JSON")
		}
		return Book{}, false
	}
	if _, err := dec.Token(); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return Book{}, false
	}

	var b Book
	details := map[string]string{}
	if in.Title != nil {
		b.Title = strings.TrimSpace(*in.Title)
	}
	if b.Title == "" {
		details["title"] = "title is required"
	}
	if in.Author != nil {
		b.Author = strings.TrimSpace(*in.Author)
	}
	if b.Author == "" {
		details["author"] = "author is required"
	}
	if in.Year != nil {
		if *in.Year < 0 {
			details["year"] = "year must not be negative"
		}
		b.Year = *in.Year
	}
	if in.ISBN != nil {
		b.ISBN = strings.TrimSpace(*in.ISBN)
	}
	if len(details) > 0 {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Details: details})
		return Book{}, false
	}
	return b, true
}

// pathID parses the {id} path value. On failure it writes the error response
// and returns false.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		log.Printf("health check: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	created, err := s.store.Create(r.Context(), b)
	if err != nil {
		writeStoreError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
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
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(r.Context(), id)
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	updated, err := s.store.Update(r.Context(), id, b)
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		writeStoreError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
