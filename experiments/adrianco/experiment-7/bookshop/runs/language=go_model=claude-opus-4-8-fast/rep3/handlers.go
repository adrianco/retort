package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
)

// Server holds the dependencies shared by the HTTP handlers.
type Server struct {
	store *Store
}

// NewServer builds an http.Handler with all routes registered.
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
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(in)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
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
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(id, in)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	err := s.store.Delete(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeInput reads and validates a BookInput from the request body. On any
// problem it writes the appropriate error response and returns ok=false.
func decodeInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return BookInput{}, false
	}
	if msg, valid := in.validate(); !valid {
		writeError(w, http.StatusBadRequest, msg)
		return BookInput{}, false
	}
	return in, true
}

// parseID extracts the {id} path value as an int64.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
