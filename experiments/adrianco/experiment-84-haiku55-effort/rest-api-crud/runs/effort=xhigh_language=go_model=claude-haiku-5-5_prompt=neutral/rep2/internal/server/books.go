package server

import (
	"errors"
	"net/http"
	"strconv"
	"strings"

	"bookapi/internal/book"
	"bookapi/internal/store"
)

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	created, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.serverError(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
}

// listBooks returns every book, optionally narrowed with ?author=. An empty
// author parameter is treated the same as no parameter.
func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.serverError(w, r, err)
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
		s.storeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

// updateBook replaces the book's fields. Title and author are required; year
// and isbn are cleared if omitted, as PUT replaces the whole resource.
func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	updated, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.storeError(w, r, err)
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
		s.storeError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBookInput parses, normalizes, and validates a book payload. On failure
// it writes the error response and returns false.
func decodeBookInput(w http.ResponseWriter, r *http.Request) (book.Input, bool) {
	var in book.Input
	if !decodeJSON(w, r, &in) {
		return book.Input{}, false
	}
	in = in.Normalize()
	if errs := in.Validate(); errs != nil {
		writeValidationError(w, errs)
		return book.Input{}, false
	}
	return in, true
}

// pathID reads the {id} path segment. On failure it writes a 400 and returns false.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "id must be an integer")
		return 0, false
	}
	return id, true
}

// storeError maps repository errors to HTTP responses.
func (s *Server) storeError(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, store.ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.serverError(w, r, err)
}

// serverError logs the underlying cause and returns a generic 500, so
// internal details never reach the client.
func (s *Server) serverError(w http.ResponseWriter, r *http.Request, err error) {
	s.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "error", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}
