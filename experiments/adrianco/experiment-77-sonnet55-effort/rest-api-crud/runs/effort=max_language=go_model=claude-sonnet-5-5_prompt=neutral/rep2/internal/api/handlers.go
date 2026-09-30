package api

import (
	"context"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"

	"bookapi/internal/book"
)

const healthTimeout = 2 * time.Second

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}
	b, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

// listBooks serves GET /books. An empty ?author= is treated as no filter.
func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

// updateBook serves PUT /books/{id}. PUT replaces the whole book, so the body
// must be complete: title and author are required, and an omitted year or ISBN
// is cleared.
func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}
	b, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.fail(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// health reports whether the service can reach its database.
func (s *server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), healthTimeout)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// pathID parses the {id} path segment. A malformed ID is a 400; a well-formed
// one that matches no book is left for the store to report as a 404.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "book id must be an integer")
		return 0, false
	}
	return id, true
}

// fail writes the response for an error from the store: 404 for a missing
// book, otherwise a generic 500 (the cause is logged, never sent to the client).
func (s *server) fail(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, book.ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "error", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}
