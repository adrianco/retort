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

// maxBodyBytes caps request bodies; a book record is tiny.
const maxBodyBytes = 1 << 20

// Server exposes the book collection over HTTP.
type Server struct {
	store *Store
}

// NewServer returns a Server backed by store.
func NewServer(store *Store) *Server {
	return &Server{store: store}
}

// Routes returns the HTTP handler for the API.
func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreate)
	mux.HandleFunc("GET /books", s.handleList)
	mux.HandleFunc("GET /books/{id}", s.handleGet)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	mux.HandleFunc("DELETE /books/{id}", s.handleDelete)
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

// writeStoreError maps a store error onto an HTTP response.
func writeStoreError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	log.Printf("store error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// parseID extracts the {id} path value, writing a 400 if it is not a
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
// error response itself when the body is unusable.
func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var in struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
			return Book{}, false
		}
		writeError(w, http.StatusBadRequest, "request body must be a valid JSON book object")
		return Book{}, false
	}
	if _, err := dec.Token(); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return Book{}, false
	}

	b := Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}
	details := map[string]string{}
	if b.Title == "" {
		details["title"] = "title is required"
	}
	if b.Author == "" {
		details["author"] = "author is required"
	}
	if b.Year < 0 {
		details["year"] = "year must not be negative"
	}
	if len(details) > 0 {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Details: details})
		return Book{}, false
	}
	return b, true
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		log.Printf("health check: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
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

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
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

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
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

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
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
