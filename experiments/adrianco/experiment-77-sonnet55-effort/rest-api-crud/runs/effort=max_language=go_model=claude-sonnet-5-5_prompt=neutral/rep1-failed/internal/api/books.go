package api

import (
	"context"
	"errors"
	"net/http"
	"net/url"
	"strconv"
	"strings"

	"bookapi/internal/book"
)

// readContext returns the context for a read from the store. A read is
// abandoned as soon as the client goes away, so that departed clients do not
// keep the database busy, and after RequestTimeout.
func readContext(r *http.Request) (context.Context, context.CancelFunc) {
	return context.WithTimeout(r.Context(), RequestTimeout)
}

// writeContext returns the context for a write to the store. A write that has
// reached the store is not abandoned when the client goes away (nor when it
// merely closes its sending side, which net/http treats the same way):
// cancelling a write while it commits could leave the response and the log
// claiming the opposite of what happened to the book. Like a read it is bounded
// by RequestTimeout, but the deadline starts here, after the body was read.
func writeContext(r *http.Request) (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.WithoutCancel(r.Context()), RequestTimeout)
}

// createBook handles POST /books.
func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	ctx, cancel := writeContext(r)
	defer cancel()
	b, err := s.store.Create(ctx, in)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	s.writeJSON(w, http.StatusCreated, b)
}

// listBooks handles GET /books, optionally filtered with ?author=.
func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	// URL.Query would silently drop a malformed pair and so ignore the filter.
	query, err := url.ParseQuery(r.URL.RawQuery)
	if err != nil {
		s.writeError(w, http.StatusBadRequest, "malformed query string")
		return
	}
	author := strings.TrimSpace(query.Get("author"))
	ctx, cancel := readContext(r)
	defer cancel()
	books, err := s.store.List(ctx, author)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	if books == nil {
		books = []book.Book{} // encode "no books" as [] rather than null
	}
	s.writeJSON(w, http.StatusOK, books)
}

// getBook handles GET /books/{id}.
func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	ctx, cancel := readContext(r)
	defer cancel()
	b, err := s.store.Get(ctx, id)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	s.writeJSON(w, http.StatusOK, b)
}

// updateBook handles PUT /books/{id}. As PUT requires, the body replaces the
// whole book: optional fields that are left out are reset.
func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	ctx, cancel := writeContext(r)
	defer cancel()
	b, err := s.store.Update(ctx, id, in)
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
	ctx, cancel := writeContext(r)
	defer cancel()
	if err := s.store.Delete(ctx, id); err != nil {
		s.storeError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// pathID parses the {id} path value. Ids are positive integers in their
// canonical form, with no sign or leading zeros, so that a book has one
// canonical URL. When ok is false the 400 response has already been written.
func (s *server) pathID(w http.ResponseWriter, r *http.Request) (id int64, ok bool) {
	raw := r.PathValue("id")
	n, err := strconv.ParseUint(raw, 10, 63)
	if err != nil || n == 0 || strconv.FormatUint(n, 10) != raw {
		s.writeError(w, http.StatusBadRequest, "book id must be a positive integer without a sign or leading zeros")
		return 0, false
	}
	return int64(n), true
}

// statusClientClosedRequest is nginx's non-standard status for a request whose
// client went away before the answer was ready. Nobody is left to read it; it
// is there for the access log.
const statusClientClosedRequest = 499

// storeError answers for a failed store call: 404 for a missing book, 499 for a
// read abandoned by a departed client, 503 when the database did not answer
// within RequestTimeout, and a generic 500 for anything else. Details of a real
// failure go to the log, never to the client.
func (s *server) storeError(w http.ResponseWriter, r *http.Request, err error) {
	switch {
	case errors.Is(err, book.ErrNotFound):
		s.writeError(w, http.StatusNotFound, "book not found")
	case errors.Is(err, context.Canceled):
		s.writeError(w, statusClientClosedRequest, "client closed request")
	case errors.Is(err, context.DeadlineExceeded):
		s.logger.Warn("store call timed out", "method", r.Method, "path", r.URL.Path, "err", err)
		s.writeError(w, http.StatusServiceUnavailable, "the database is busy, try again shortly")
	default:
		s.logger.Error("store failure", "method", r.Method, "path", r.URL.Path, "err", err)
		s.writeError(w, http.StatusInternalServerError, "internal server error")
	}
}
