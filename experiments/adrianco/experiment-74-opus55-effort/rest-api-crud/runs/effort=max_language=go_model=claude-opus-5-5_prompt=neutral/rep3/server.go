package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"runtime/debug"
	"time"
)

// server holds the dependencies shared by the HTTP handlers.
type server struct {
	store  *Store
	logger *slog.Logger
}

// NewHandler returns the HTTP handler for the book API, backed by store.
func NewHandler(store *Store, logger *slog.Logger) http.Handler {
	s := &server{store: store, logger: logger}
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("GET /books", s.handleListBooks)
	mux.HandleFunc("POST /books", s.handleCreateBook)
	mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)

	// Catch-alls, so that unsupported methods and unknown paths get JSON
	// errors too; ServeMux's own 404 and 405 replies are plain text. The
	// method-specific patterns above take precedence over these.
	mux.Handle("/health", methodNotAllowed("GET, HEAD"))
	mux.Handle("/books", methodNotAllowed("GET, HEAD, POST"))
	mux.Handle("/books/{id}", methodNotAllowed("GET, HEAD, PUT, DELETE"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusNotFound, errorResponse{Error: "resource not found"})
	})

	return s.logRequests(s.recoverPanics(mux))
}

func methodNotAllowed(allow string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeJSON(w, http.StatusMethodNotAllowed, errorResponse{Error: "method not allowed"})
	})
}

// errorResponse is the body of every error reply.
type errorResponse struct {
	Error  string          `json:"error"`
	Fields ValidationError `json:"fields,omitempty"` // per-field problems, for 400s
}

// writeJSON sends v as a JSON response with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false) // keep "&" in titles readable
	if err := enc.Encode(v); err != nil {
		// Only possible for unencodable types, i.e. a programming error.
		status = http.StatusInternalServerError
		buf.Reset()
		buf.WriteString(`{"error":"internal server error"}` + "\n")
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(buf.Bytes())
}

// writeError replies with the status and message appropriate to err. Errors
// that are not the client's fault are logged and reported as a generic 500 so
// that internal details never reach clients.
func (s *server) writeError(w http.ResponseWriter, r *http.Request, err error) {
	var validationErr ValidationError
	var reqErr *requestError
	switch {
	case errors.As(err, &validationErr):
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: validationErr.Error(), Fields: validationErr})
	case errors.As(err, &reqErr):
		writeJSON(w, reqErr.status, errorResponse{Error: reqErr.msg})
	case errors.Is(err, ErrNotFound):
		writeJSON(w, http.StatusNotFound, errorResponse{Error: "book not found"})
	default:
		s.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "err", err)
		writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "internal server error"})
	}
}

// logRequests logs the method, path, status and duration of every request.
func (s *server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.logger.Info("request", "method", r.Method, "path", r.URL.Path,
			"status", rec.status, "duration", time.Since(start))
	})
}

// statusRecorder remembers the status code a handler sends.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (rec *statusRecorder) WriteHeader(status int) {
	rec.status = status
	rec.ResponseWriter.WriteHeader(status)
}

// Unwrap gives http.ResponseController access to the underlying writer.
func (rec *statusRecorder) Unwrap() http.ResponseWriter {
	return rec.ResponseWriter
}

// recoverPanics answers a panicking request with a JSON 500 instead of letting
// net/http drop the connection, and logs the panic with its stack trace.
func (s *server) recoverPanics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			v := recover()
			if v == nil {
				return
			}
			if v == http.ErrAbortHandler {
				panic(v) // a deliberate abort: let net/http handle it
			}
			s.logger.Error("panic serving request", "method", r.Method, "path", r.URL.Path,
				"panic", v, "stack", string(debug.Stack()))
			writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "internal server error"})
		}()
		next.ServeHTTP(w, r)
	})
}
