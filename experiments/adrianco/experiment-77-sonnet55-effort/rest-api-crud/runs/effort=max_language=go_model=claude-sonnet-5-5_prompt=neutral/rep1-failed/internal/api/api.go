// Package api implements the HTTP interface of the book service.
package api

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"bookapi/internal/book"
)

// healthTimeout bounds how long the health check waits for the database.
const healthTimeout = 2 * time.Second

// RequestTimeout bounds how long one request may wait for its turn at the store
// and use it. A write can then wait a further store.BusyTimeout for a lock held
// by another process, which this deadline cannot interrupt, so the HTTP server
// that hosts the API should allow for both when it sets its own timeouts.
const RequestTimeout = 8 * time.Second

// BookStore is the persistence the API relies on; *store.Store implements it.
type BookStore interface {
	Create(ctx context.Context, in book.Input) (book.Book, error)
	Get(ctx context.Context, id int64) (book.Book, error)
	List(ctx context.Context, author string) ([]book.Book, error)
	Update(ctx context.Context, id int64, in book.Input) (book.Book, error)
	Delete(ctx context.Context, id int64) error
	Ping(ctx context.Context) error
}

type server struct {
	store  BookStore
	logger *slog.Logger
}

// New returns the handler that serves the book API on top of store. A nil
// logger selects slog.Default.
func New(store BookStore, logger *slog.Logger) http.Handler {
	if logger == nil {
		logger = slog.Default()
	}
	s := &server{store: store, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)

	// For a known path with an unsupported method the mux would answer with a
	// plain-text 405. The method-less patterns below are less specific than
	// the ones above, so they only receive the remaining methods and let us
	// answer in JSON. The catch-all does the same for unknown paths.
	mux.HandleFunc("/health", s.methodNotAllowed(http.MethodGet, http.MethodHead))
	mux.HandleFunc("/books", s.methodNotAllowed(http.MethodGet, http.MethodHead, http.MethodPost))
	mux.HandleFunc("/books/{id}", s.methodNotAllowed(http.MethodGet, http.MethodHead, http.MethodPut, http.MethodDelete))
	mux.HandleFunc("/", s.notFound)

	return s.logRequests(s.recoverPanics(mux))
}

// health reports whether the service can reach its database.
func (s *server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), healthTimeout)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		if errors.Is(err, context.Canceled) {
			s.writeError(w, statusClientClosedRequest, "client closed request")
			return
		}
		s.logger.Error("health check failed", "err", err)
		s.writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	s.writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) methodNotAllowed(allowed ...string) http.HandlerFunc {
	allow := strings.Join(allowed, ", ")
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		s.writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) notFound(w http.ResponseWriter, r *http.Request) {
	s.writeError(w, http.StatusNotFound, "not found")
}
