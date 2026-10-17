// Package server exposes the book collection over a JSON HTTP API.
package server

import (
	"log/slog"
	"net/http"
	"strings"
	"time"

	"bookapi/internal/store"
)

// Server holds the dependencies needed to serve HTTP requests.
type Server struct {
	store  *store.Store
	logger *slog.Logger
}

// New returns a Server backed by st. Requests are logged to logger.
func New(st *store.Store, logger *slog.Logger) *Server {
	return &Server{store: st, logger: logger}
}

// Handler returns the routed HTTP handler for the API.
//
// Routes are registered with Go 1.22 method patterns. The method-less patterns
// below them catch requests whose method isn't supported so the response is a
// JSON 405 with an Allow header, and "/" turns any other unmatched path into a
// JSON 404.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("/health", methodNotAllowed("GET"))

	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("/books", methodNotAllowed("GET", "POST"))

	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	mux.HandleFunc("/books/{id}", methodNotAllowed("GET", "PUT", "DELETE"))

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "route not found")
	})

	return s.logRequests(mux)
}

// health reports 200 when the database answers a ping and 503 otherwise.
func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		s.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func methodNotAllowed(allowed ...string) http.HandlerFunc {
	allow := strings.Join(allowed, ", ")
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// statusRecorder captures the status code written by a downstream handler so
// the request logger can report it.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.logger.Info("request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rec.status,
			"duration", time.Since(start),
		)
	})
}
