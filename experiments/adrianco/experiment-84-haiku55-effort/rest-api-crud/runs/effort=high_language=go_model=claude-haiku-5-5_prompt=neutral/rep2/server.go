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
)

// maxBodyBytes caps the size of request bodies.
const maxBodyBytes = 1 << 20

type server struct {
	store *Store
}

// NewHandler returns the HTTP handler for the book API.
func NewHandler(store *Store) http.Handler {
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

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		log.Printf("health check: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	f, ok := decodeBookFields(w, r)
	if !ok {
		return
	}

	book, err := s.store.Create(r.Context(), f)
	if err != nil {
		serverError(w, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))

	books, err := s.store.List(r.Context(), author)
	if err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}

	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// updateBook replaces the book with the request body. As with create, title
// and author are required; omitted year and isbn are cleared.
func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	f, ok := decodeBookFields(w, r)
	if !ok {
		return
	}

	book, err := s.store.Update(r.Context(), id, f)
	if err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}

	if err := s.store.Delete(r.Context(), id); err != nil {
		storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBookFields reads, normalizes and validates a book from the request
// body. On failure it writes the error response and returns false.
func decodeBookFields(w http.ResponseWriter, r *http.Request) (BookFields, bool) {
	var f BookFields
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)

	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(&f); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return f, false
	}
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return f, false
	}

	f.Normalize()
	if err := f.Validate(); err != nil {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]any{
			"error":  err.Error(),
			"fields": err,
		})
		return f, false
	}
	return f, true
}

// parseID reads the {id} path segment. It must be a positive integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

func storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
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
