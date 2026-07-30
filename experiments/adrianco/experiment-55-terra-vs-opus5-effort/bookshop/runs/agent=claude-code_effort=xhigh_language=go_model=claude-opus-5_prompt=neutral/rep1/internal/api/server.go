// Package api exposes the book collection over HTTP.
package api

import (
	"log/slog"
	"net/http"
	"strings"
	"time"

	"bookapi/internal/books"
)

// Server routes HTTP requests to the book store. Construct it with NewServer;
// it implements http.Handler.
type Server struct {
	store   *books.Store
	logger  *slog.Logger
	now     func() time.Time
	handler http.Handler
}

// Option customises a Server.
type Option func(*Server)

// WithClock overrides the clock used for validation, which bounds how far in
// the future a publication year may be. Tests use it to pin "now".
func WithClock(now func() time.Time) Option {
	return func(s *Server) { s.now = now }
}

// NewServer builds the HTTP handler for the API. A nil logger discards logs.
func NewServer(store *books.Store, logger *slog.Logger, opts ...Option) *Server {
	if logger == nil {
		logger = slog.New(slog.DiscardHandler)
	}
	s := &Server{store: store, logger: logger, now: time.Now}
	for _, opt := range opts {
		opt(s)
	}
	// logRequests sits outermost so that even a panicking request produces an
	// access-log line — and so recoverPanic can see the recorded status and
	// tell "nothing written yet" from "response already in flight".
	s.handler = s.logRequests(s.recoverPanic(s.routes()))
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.handler.ServeHTTP(w, r)
}

// routes wires up the URL patterns.
//
// Each resource is registered twice: once per supported method, and once
// method-less as a fallback. Go's ServeMux prefers the more specific
// method-bound pattern, so the fallback only fires on a method mismatch —
// which is how a wrong method gets a JSON 405 with an Allow header instead of
// the mux's built-in plain-text response.
func (s *Server) routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("/health", methodNotAllowed(s, http.MethodGet))

	mux.HandleFunc("POST /books", s.handleCreateBook)
	mux.HandleFunc("GET /books", s.handleListBooks)
	mux.HandleFunc("/books", methodNotAllowed(s, http.MethodGet, http.MethodPost))

	mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)
	mux.HandleFunc("/books/{id}", methodNotAllowed(s, http.MethodGet, http.MethodPut, http.MethodDelete))

	mux.HandleFunc("/", s.handleNotFound)

	return mux
}

func methodNotAllowed(s *Server, allowed ...string) http.HandlerFunc {
	allow := strings.Join(allowed, ", ")
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		s.respondError(w, r, errorf(http.StatusMethodNotAllowed,
			"method %s is not allowed on %s; allowed: %s", r.Method, r.URL.Path, allow))
	}
}

func (s *Server) handleNotFound(w http.ResponseWriter, r *http.Request) {
	s.respondError(w, r, errorf(http.StatusNotFound, "no route matches %s %s", r.Method, r.URL.Path))
}
