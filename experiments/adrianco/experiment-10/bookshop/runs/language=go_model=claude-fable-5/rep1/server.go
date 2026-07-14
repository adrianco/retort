package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// Server is the HTTP layer over a Store.
type Server struct {
	store *Store
	mux   *http.ServeMux
}

func NewServer(store *Store) *Server {
	s := &Server{store: store, mux: http.NewServeMux()}
	s.mux.HandleFunc("GET /health", s.handleHealth)
	s.mux.HandleFunc("POST /books", s.handleCreate)
	s.mux.HandleFunc("GET /books", s.handleList)
	s.mux.HandleFunc("GET /books/{id}", s.handleGet)
	s.mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	s.mux.HandleFunc("DELETE /books/{id}", s.handleDelete)
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// bookInput is the request body for create/update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func decodeBook(r *http.Request) (*bookInput, string) {
	var in bookInput
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		return nil, "invalid JSON body: " + err.Error()
	}
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	if in.Title == "" {
		return nil, "title is required"
	}
	if in.Author == "" {
		return nil, "author is required"
	}
	if in.Year < 0 {
		return nil, "year must not be negative"
	}
	return &in, ""
}

func pathID(r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	return id, err == nil && id > 0
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, msg := decodeBook(r)
	if msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}
	b := &Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
	if err := s.store.Create(b); err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.URL.Query().Get("author"))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	b, err := s.store.Get(id)
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

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	in, msg := decodeBook(r)
	if msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}
	b := &Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
	err := s.store.Update(b)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "invalid book id")
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
