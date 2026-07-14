package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
)

// Server holds dependencies for the HTTP handlers.
type Server struct {
	store *Store
}

// NewServer constructs a Server backed by the given store.
func NewServer(store *Store) *Server {
	return &Server{store: store}
}

// Routes returns an http.Handler with all routes registered. It relies on the
// method-aware pattern matching added to net/http in Go 1.22+.
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

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := b.validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := s.store.Create(b); err != nil {
		log.Printf("create book: %v", err)
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := s.store.List(author)
	if err != nil {
		log.Printf("list books: %v", err)
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	book, err := s.store.Get(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		log.Printf("get book: %v", err)
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := b.validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := s.store.Update(id, b); errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		log.Printf("update book: %v", err)
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	if err := s.store.Delete(id); errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		log.Printf("delete book: %v", err)
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// --- helpers ---

func parseID(r *http.Request) (int64, error) {
	return strconv.ParseInt(r.PathValue("id"), 10, 64)
}

func decodeBook(r *http.Request) (*Book, error) {
	var b Book
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&b); err != nil {
		return nil, errors.New("invalid JSON body")
	}
	return &b, nil
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("encode response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
