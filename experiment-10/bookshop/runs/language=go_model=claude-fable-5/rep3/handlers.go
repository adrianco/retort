package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// Server holds the HTTP handlers and their dependencies.
type Server struct {
	store *Store
}

// NewServer returns an http.Handler with all routes registered.
func NewServer(store *Store) http.Handler {
	s := &Server{store: store}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreateBook)
	mux.HandleFunc("GET /books", s.handleListBooks)
	mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)
	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// decodeBook parses and validates the request body. It returns a
// human-readable error message when the input is invalid.
func decodeBook(r *http.Request) (Book, string) {
	var b Book
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&b); err != nil {
		return Book{}, "invalid JSON body: " + err.Error()
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" {
		return Book{}, "title is required"
	}
	if b.Author == "" {
		return Book{}, "author is required"
	}
	return b, ""
}

func pathID(r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	return id, err == nil && id > 0
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	b, msg := decodeBook(r)
	if msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}
	created, err := s.store.CreateBook(b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.ListBooks(r.URL.Query().Get("author"))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGetBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	b, err := s.store.GetBook(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	b, msg := decodeBook(r)
	if msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}
	updated, err := s.store.UpdateBook(id, b)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	err := s.store.DeleteBook(id)
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
