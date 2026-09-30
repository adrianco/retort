// Package api implements the HTTP interface of the book service.
package api

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"bookapi/internal/store"
)

// BookStore is the persistence the API depends on.
type BookStore interface {
	Create(ctx context.Context, in store.Input) (store.Book, error)
	Get(ctx context.Context, id int64) (store.Book, error)
	List(ctx context.Context, author string) ([]store.Book, error)
	Update(ctx context.Context, id int64, in store.Input) (store.Book, error)
	Delete(ctx context.Context, id int64) error
	Ping(ctx context.Context) error
}

type server struct {
	store  BookStore
	logger *slog.Logger
}

// New returns the HTTP handler serving the book API backed by bs.
func New(bs BookStore, logger *slog.Logger) http.Handler {
	if logger == nil {
		logger = slog.New(slog.DiscardHandler)
	}
	s := &server{store: bs, logger: logger}

	mux := http.NewServeMux()
	route(mux, "/health", methods{http.MethodGet: s.health})
	route(mux, "/books", methods{
		http.MethodGet:  s.listBooks,
		http.MethodPost: s.createBook,
	})
	route(mux, "/books/{id}", methods{
		http.MethodGet:    s.getBook,
		http.MethodPut:    s.updateBook,
		http.MethodDelete: s.deleteBook,
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "not found")
	})

	return recoverer(logger, requestLogger(logger, mux))
}

type methods map[string]http.HandlerFunc

// route registers pattern and dispatches on the request method itself so that
// 405 responses are JSON and carry an Allow header. HEAD is served by GET.
func route(mux *http.ServeMux, pattern string, m methods) {
	allowed := make([]string, 0, len(m)+1)
	for method := range m {
		allowed = append(allowed, method)
	}
	if _, ok := m[http.MethodGet]; ok {
		allowed = append(allowed, http.MethodHead)
	}
	sort.Strings(allowed)
	allow := strings.Join(allowed, ", ")

	mux.HandleFunc(pattern, func(w http.ResponseWriter, r *http.Request) {
		method := r.Method
		if method == http.MethodHead {
			method = http.MethodGet
		}
		h, ok := m[method]
		if !ok {
			w.Header().Set("Allow", allow)
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		h(w, r)
	})
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := readBook(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.serverError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	in, ok := readBook(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// storeError maps a store error to a response: 404 for a missing book,
// otherwise a generic 500.
func (s *server) storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, store.ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.serverError(w, err)
}

// serverError logs err and responds with a 500 that does not leak details.
func (s *server) serverError(w http.ResponseWriter, err error) {
	s.logger.Error("request failed", "error", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// bookID parses the {id} path value, writing a 400 if it is not a positive
// integer.
func bookID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("invalid book id %q", raw))
		return 0, false
	}
	return id, true
}
