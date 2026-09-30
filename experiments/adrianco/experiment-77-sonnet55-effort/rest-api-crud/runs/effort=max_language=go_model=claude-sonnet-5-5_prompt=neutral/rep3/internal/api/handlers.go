package api

import (
	"context"
	"errors"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"bookapi/internal/book"
)

const healthTimeout = 2 * time.Second

// health reports whether the service can reach its database.
func (s *server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), healthTimeout)
	defer cancel()

	if err := s.store.Ping(ctx); err != nil {
		s.log.Error("health check failed", "err", err)
		s.writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	s.writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// createBook handles POST /books.
func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	b, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	s.writeJSON(w, http.StatusCreated, b)
}

// listBooks handles GET /books, optionally filtered by ?author=.
func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	// Parse the query strictly: r.URL.Query() silently drops malformed pairs,
	// which would turn a broken ?author= filter into an unfiltered listing.
	query, err := url.ParseQuery(r.URL.RawQuery)
	if err != nil {
		s.writeError(w, http.StatusBadRequest, "malformed query string")
		return
	}
	books, err := s.store.List(r.Context(), strings.TrimSpace(query.Get("author")))
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	if books == nil {
		books = []book.Book{} // encode as [] rather than null
	}
	s.writeJSON(w, http.StatusOK, books)
}

// getBook handles GET /books/{id}.
func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	s.writeJSON(w, http.StatusOK, b)
}

// updateBook handles PUT /books/{id}. As PUT requires, the request replaces the
// whole book: the optional fields it leaves out are cleared.
func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	b, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	s.writeJSON(w, http.StatusOK, b)
}

// deleteBook handles DELETE /books/{id}.
func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.storeError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (s *server) notFound(w http.ResponseWriter, r *http.Request) {
	s.writeError(w, http.StatusNotFound, "endpoint not found")
}

func (s *server) methodNotAllowed(allow string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		s.writeError(w, http.StatusMethodNotAllowed, "method "+r.Method+" is not allowed on this endpoint")
	}
}

// pathID parses the {id} path segment. On failure it writes the 400 response
// itself and reports false.
func (s *server) pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		s.writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

// statusClientClosedRequest is the non-standard code nginx logs when a client
// hangs up before the response. Nobody receives it; it only keeps such requests
// out of the 5xx statistics of the access log.
const statusClientClosedRequest = 499

// storeError answers for a failed store call: 404 for an unknown book, nothing
// worth reporting when the client has hung up, and a generic 500 for anything
// else, whose details are logged rather than leaked.
func (s *server) storeError(w http.ResponseWriter, r *http.Request, err error) {
	switch {
	case errors.Is(err, book.ErrNotFound):
		s.writeError(w, http.StatusNotFound, "book not found")
	case errors.Is(err, context.Canceled):
		w.WriteHeader(statusClientClosedRequest)
	default:
		s.log.Error("store operation failed", "method", r.Method, "path", r.URL.Path, "err", err)
		s.writeError(w, http.StatusInternalServerError, "internal server error")
	}
}
