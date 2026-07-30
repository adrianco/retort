package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// Server holds the HTTP handlers for the book API.
type Server struct {
	store *Store
}

// NewServer builds a router serving the book API over store.
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

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if v != nil {
		json.NewEncoder(w).Encode(v)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// decodeBook parses and validates a book payload from the request body.
func decodeBook(r *http.Request) (Book, error) {
	var b Book
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&b); err != nil {
		return Book{}, errors.New("invalid JSON body")
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	if b.Title == "" {
		return Book{}, errors.New("title is required")
	}
	if b.Author == "" {
		return Book{}, errors.New("author is required")
	}
	return b, nil
}

// pathID extracts and validates the {id} path segment.
func pathID(r *http.Request) (int64, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		return 0, errors.New("invalid book id")
	}
	return id, nil
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	created, err := s.store.Create(b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	b, err := s.store.Get(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	updated, err := s.store.Update(id, b)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	err = s.store.Delete(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
