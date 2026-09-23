package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"runtime/debug"
	"strconv"
	"time"
)

// maxBodyBytes caps request bodies; a book is a few hundred bytes at most.
const maxBodyBytes = 1 << 20

// Server exposes the book store over HTTP.
type Server struct {
	store  *Store
	logger *slog.Logger
}

// NewServer returns the fully wired HTTP handler: routes plus logging and panic
// recovery middleware. Every response, including errors, is JSON.
func NewServer(store *Store, logger *slog.Logger) http.Handler {
	s := &Server{store: store, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreateBook)
	mux.HandleFunc("GET /books", s.handleListBooks)
	mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)

	// Method-less patterns are less specific than the ones above, so they only
	// catch known paths requested with an unsupported method. They replace the
	// mux's built-in plain-text 405/404 responses with JSON ones.
	mux.Handle("/health", methodNotAllowed("GET, HEAD"))
	mux.Handle("/books", methodNotAllowed("GET, HEAD, POST"))
	mux.Handle("/books/{id}", methodNotAllowed("GET, HEAD, PUT, DELETE"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "resource not found")
	})

	return s.middleware(mux)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status": "unavailable",
			"error":  "database unreachable",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	in, ok := s.readBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.internalError(w, r, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		s.internalError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGetBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// handleUpdateBook implements PUT as a full replacement: omitted optional fields
// (year, isbn) are cleared, and title/author are required just as on create.
func (s *Server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := s.readBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.storeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.storeError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// readBookInput decodes, normalizes and validates a book body. On failure it has
// already written the error response and returns ok=false.
func (s *Server) readBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	if status, msg := decodeJSON(w, r, &in); status != 0 {
		writeError(w, status, msg)
		return BookInput{}, false
	}
	in.Normalize()
	if fields := in.Validate(); len(fields) > 0 {
		writeJSON(w, http.StatusBadRequest, validationErrorResponse{
			Error:  "validation failed",
			Fields: fields,
		})
		return BookInput{}, false
	}
	return in, true
}

func (s *Server) storeError(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.internalError(w, r, err)
}

// internalError logs the real cause and returns a generic message, so database
// details never leak to clients.
func (s *Server) internalError(w http.ResponseWriter, r *http.Request, err error) {
	s.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "err", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// parseID extracts the {id} path segment, writing a 400 if it is not a positive integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

// decodeJSON decodes a single JSON object from the request body into dst. It
// returns a zero status on success, otherwise the HTTP status and a client-safe
// message describing what was wrong with the body.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) (int, string) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)

	err := dec.Decode(dst)
	if err == nil {
		// Reject trailing content such as a second JSON value.
		if dec.Decode(&struct{}{}) != io.EOF {
			return http.StatusBadRequest, "request body must contain a single JSON object"
		}
		return 0, ""
	}

	var (
		syntaxErr   *json.SyntaxError
		typeErr     *json.UnmarshalTypeError
		tooLargeErr *http.MaxBytesError
	)
	switch {
	case errors.Is(err, io.EOF):
		return http.StatusBadRequest, "request body must not be empty"
	case errors.As(err, &tooLargeErr):
		return http.StatusRequestEntityTooLarge,
			fmt.Sprintf("request body must not exceed %d bytes", tooLargeErr.Limit)
	case errors.As(err, &syntaxErr):
		return http.StatusBadRequest,
			fmt.Sprintf("malformed JSON at byte offset %d", syntaxErr.Offset)
	case errors.Is(err, io.ErrUnexpectedEOF):
		return http.StatusBadRequest, "malformed JSON: unexpected end of input"
	case errors.As(err, &typeErr):
		if typeErr.Field == "" {
			return http.StatusBadRequest, "request body must be a JSON object"
		}
		return http.StatusBadRequest,
			fmt.Sprintf("field %q must be of type %s", typeErr.Field, typeErr.Type)
	default:
		return http.StatusBadRequest, "invalid request body"
	}
}

type errorResponse struct {
	Error string `json:"error"`
}

type validationErrorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// The status line is already sent, so an encoding error can't be reported to
	// the client; it can only mean the connection went away.
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func methodNotAllowed(allow string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	})
}

// middleware logs each request and converts panics into JSON 500 responses.
func (s *Server) middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w}

		defer func() {
			if p := recover(); p != nil {
				if p == http.ErrAbortHandler {
					panic(p)
				}
				s.logger.Error("panic serving request",
					"method", r.Method, "path", r.URL.Path, "panic", p, "stack", string(debug.Stack()))
				if !rec.wroteHeader {
					writeError(rec, http.StatusInternalServerError, "internal server error")
				}
			}
			s.logger.Info("request",
				"method", r.Method,
				"path", r.URL.Path,
				"status", rec.status(),
				"duration", time.Since(start))
		}()

		next.ServeHTTP(rec, r)
	})
}

// statusRecorder captures the response status for logging.
type statusRecorder struct {
	http.ResponseWriter
	code        int
	wroteHeader bool
}

func (rec *statusRecorder) WriteHeader(code int) {
	if !rec.wroteHeader {
		rec.code = code
		rec.wroteHeader = true
	}
	rec.ResponseWriter.WriteHeader(code)
}

func (rec *statusRecorder) Write(b []byte) (int, error) {
	if !rec.wroteHeader {
		rec.WriteHeader(http.StatusOK)
	}
	return rec.ResponseWriter.Write(b)
}

func (rec *statusRecorder) status() int {
	if !rec.wroteHeader {
		return http.StatusOK
	}
	return rec.code
}

// Unwrap lets http.ResponseController reach the underlying writer.
func (rec *statusRecorder) Unwrap() http.ResponseWriter { return rec.ResponseWriter }
