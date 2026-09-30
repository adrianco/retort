// Package api implements the HTTP interface of the book service.
package api

import (
	"context"
	"log/slog"
	"net/http"

	"bookapi/internal/book"
)

// BookStore is the persistence the API depends on; *store.Store implements it.
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

// New returns the handler that serves the API on top of store. A nil logger
// falls back to slog.Default.
func New(store BookStore, logger *slog.Logger) http.Handler {
	if logger == nil {
		logger = slog.Default()
	}
	s := &server{store: store, logger: logger}

	// Method-less patterns are fallbacks: the method-specific pattern for the
	// same path is more specific and wins, so these only see the other methods.
	mux := http.NewServeMux()
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("/books", methodNotAllowed("GET, HEAD, POST"))
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	mux.HandleFunc("/books/{id}", methodNotAllowed("DELETE, GET, HEAD, PUT"))
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("/health", methodNotAllowed("GET, HEAD"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "resource not found")
	})

	return observe(logger, mux)
}

// methodNotAllowed answers with a JSON 405 (the mux's own is plain text).
func methodNotAllowed(allow string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}
