// Package api serves the book collection over HTTP as a JSON REST API.
package api

import (
	"context"
	"log/slog"
	"net/http"

	"bookapi/internal/book"
)

// BookStore is the persistence the API needs. *sqlite.Store implements it.
// Get, Update and Delete return book.ErrNotFound for an unknown ID.
type BookStore interface {
	Create(ctx context.Context, in book.Input) (book.Book, error)
	Get(ctx context.Context, id int64) (book.Book, error)
	List(ctx context.Context, author string) ([]book.Book, error)
	Update(ctx context.Context, id int64, in book.Input) (book.Book, error)
	Delete(ctx context.Context, id int64) error
	Ping(ctx context.Context) error
}

type server struct {
	store BookStore
	log   *slog.Logger
}

// New returns the HTTP handler serving the API on top of store. A nil logger
// means slog.Default().
func New(store BookStore, logger *slog.Logger) http.Handler {
	if logger == nil {
		logger = slog.Default()
	}
	s := &server{store: store, log: logger}
	return s.logAndRecover(s.routes())
}

// routes maps every endpoint to its handler. Each path also gets a method-less
// fallback so that a wrong method yields a JSON 405 with an Allow header, and
// the "/" catch-all turns unknown paths into a JSON 404; the mux would
// otherwise answer both with plain text. (A GET route also serves HEAD.)
func (s *server) routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("/health", s.methodNotAllowed("GET, HEAD"))

	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("/books", s.methodNotAllowed("GET, HEAD, POST"))

	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	mux.HandleFunc("/books/{id}", s.methodNotAllowed("GET, HEAD, PUT, DELETE"))

	mux.HandleFunc("/", s.notFound)
	return mux
}
