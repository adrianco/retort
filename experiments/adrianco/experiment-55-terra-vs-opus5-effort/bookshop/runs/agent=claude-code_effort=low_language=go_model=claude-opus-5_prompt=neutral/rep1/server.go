package main

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"
)

// Server wires HTTP routes to the store.
type Server struct {
	store *Store
	mux   *http.ServeMux
}

// NewServer builds the router.
func NewServer(store *Store) *Server {
	s := &Server{store: store, mux: http.NewServeMux()}
	s.mux.HandleFunc("GET /health", s.health)
	s.mux.HandleFunc("POST /books", s.createBook)
	s.mux.HandleFunc("GET /books", s.listBooks)
	s.mux.HandleFunc("GET /books/{id}", s.getBook)
	s.mux.HandleFunc("PUT /books/{id}", s.updateBook)
	s.mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) { s.mux.ServeHTTP(w, r) }

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if v != nil {
		_ = json.NewEncoder(w).Encode(v)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// decodeBook reads and validates a book payload from the request body.
func decodeBook(r *http.Request) (Book, error) {
	var b Book
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&b); err != nil {
		return b, errors.New("invalid JSON body")
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	switch {
	case b.Title == "":
		return b, errors.New("title is required")
	case b.Author == "":
		return b, errors.New("author is required")
	case b.Year != 0 && (b.Year < 1 || b.Year > 3000):
		return b, errors.New("year must be between 1 and 3000")
	}
	return b, nil
}

func pathID(r *http.Request) (int64, error) {
	return strconv.ParseInt(r.PathValue("id"), 10, 64)
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := s.store.Create(&b); err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "id must be an integer")
		return
	}
	b, err := s.store.Get(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		writeError(w, http.StatusInternalServerError, "could not fetch book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "id must be an integer")
		return
	}
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := s.store.Update(id, &b); errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "id must be an integer")
		return
	}
	if err := s.store.Delete(id); errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
