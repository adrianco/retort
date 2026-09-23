package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"reflect"
	"strconv"
	"time"
)

const maxBodyBytes = 1 << 20 // 1 MiB

// Server is the HTTP API for the book collection.
type Server struct {
	store   *Store
	logger  *slog.Logger
	mux     *http.ServeMux
	handler http.Handler
}

// NewServer wires the API routes onto store.
func NewServer(store *Store, logger *slog.Logger) *Server {
	s := &Server{store: store, logger: logger, mux: http.NewServeMux()}
	s.mux.HandleFunc("GET /health", s.handleHealth)
	s.mux.HandleFunc("POST /books", s.handleCreateBook)
	s.mux.HandleFunc("GET /books", s.handleListBooks)
	s.mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	s.mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	s.mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)
	s.handler = s.logRequests(s.recoverPanics(http.HandlerFunc(s.route)))
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.handler.ServeHTTP(w, r)
}

// route dispatches to the mux, converting the mux's plain-text 404 and 405
// responses for unmatched requests into JSON so every error has one shape.
func (s *Server) route(w http.ResponseWriter, r *http.Request) {
	if _, pattern := s.mux.Handler(r); pattern == "" {
		w = &jsonErrorWriter{ResponseWriter: w}
	}
	s.mux.ServeHTTP(w, r)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable", "database": "unreachable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "database": "ok"})
}

func (s *Server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	in, ok := s.readBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), ListFilter{Author: r.URL.Query().Get("author")})
	if err != nil {
		s.writeStoreError(w, r, err)
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
		s.writeStoreError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

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
		s.writeStoreError(w, r, err)
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
		s.writeStoreError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// readBookInput decodes and validates the request body, writing a 4xx
// response and returning false if it is unacceptable.
func (s *Server) readBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	if status, err := decodeJSON(w, r, &in); err != nil {
		writeError(w, status, err.Error())
		return BookInput{}, false
	}
	in, err := in.Normalize(time.Now())
	if err != nil {
		var fields ValidationError
		errors.As(err, &fields)
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Fields: fields})
		return BookInput{}, false
	}
	return in, true
}

func (s *Server) writeStoreError(w http.ResponseWriter, r *http.Request, err error) {
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, err.Error())
	case errors.Is(err, ErrDuplicateISBN):
		writeError(w, http.StatusConflict, err.Error())
	default:
		s.logger.Error("store operation failed", "method", r.Method, "path", r.URL.Path, "err", err)
		writeError(w, http.StatusInternalServerError, "internal server error")
	}
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id: must be a positive integer")
		return 0, false
	}
	return id, true
}

// decodeJSON reads a single JSON object from the request body into dst. On
// failure it returns the HTTP status to respond with and a client-facing error.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) (int, error) {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	err := dec.Decode(dst)
	if err == nil {
		// Reject trailing content such as a second JSON value.
		if err = dec.Decode(&struct{}{}); errors.Is(err, io.EOF) {
			return 0, nil
		}
		if err == nil || !isMaxBytes(err) {
			return http.StatusBadRequest, errors.New("request body must contain a single JSON object")
		}
	}

	var (
		syntaxErr *json.SyntaxError
		typeErr   *json.UnmarshalTypeError
	)
	switch {
	case isMaxBytes(err):
		return http.StatusRequestEntityTooLarge, fmt.Errorf("request body must not exceed %d bytes", maxBodyBytes)
	case errors.Is(err, io.EOF):
		return http.StatusBadRequest, errors.New("request body must not be empty")
	case errors.As(err, &syntaxErr):
		return http.StatusBadRequest, fmt.Errorf("request body contains malformed JSON at offset %d", syntaxErr.Offset)
	case errors.Is(err, io.ErrUnexpectedEOF):
		return http.StatusBadRequest, errors.New("request body contains malformed JSON")
	case errors.As(err, &typeErr) && typeErr.Field == "":
		return http.StatusBadRequest, errors.New("request body must be a JSON object")
	case errors.As(err, &typeErr):
		return http.StatusBadRequest, fmt.Errorf("field %q must be %s", typeErr.Field, describeType(typeErr.Type))
	default:
		return http.StatusBadRequest, errors.New("request body could not be decoded")
	}
}

func isMaxBytes(err error) bool {
	var maxErr *http.MaxBytesError
	return errors.As(err, &maxErr)
}

func describeType(t reflect.Type) string {
	for t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	switch t.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return "an integer"
	case reflect.String:
		return "a string"
	default:
		return "of type " + t.String()
	}
}

type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	body, err := json.Marshal(v)
	if err != nil {
		status = http.StatusInternalServerError
		body = []byte(`{"error":"internal server error"}`)
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write(append(body, '\n'))
}

// jsonErrorWriter replaces the plain-text body of a 404 or 405 response with
// a JSON error, keeping headers such as Allow.
type jsonErrorWriter struct {
	http.ResponseWriter
	replaced bool
}

func (w *jsonErrorWriter) WriteHeader(status int) {
	if status != http.StatusNotFound && status != http.StatusMethodNotAllowed {
		w.ResponseWriter.WriteHeader(status)
		return
	}
	w.replaced = true
	w.Header().Del("Content-Length")
	msg := "resource not found"
	if status == http.StatusMethodNotAllowed {
		msg = "method not allowed"
	}
	writeError(w.ResponseWriter, status, msg)
}

func (w *jsonErrorWriter) Write(b []byte) (int, error) {
	if w.replaced {
		return len(b), nil
	}
	return w.ResponseWriter.Write(b)
}

// statusRecorder captures the response status for request logging.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	if r.status == 0 {
		r.status = status
	}
	r.ResponseWriter.WriteHeader(status)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	if r.status == 0 {
		r.status = http.StatusOK
	}
	return r.ResponseWriter.Write(b)
}

func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w}
		next.ServeHTTP(rec, r)
		s.logger.Info("request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rec.status,
			"duration", time.Since(start))
	})
}

func (s *Server) recoverPanics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			v := recover()
			if v == nil {
				return
			}
			if v == http.ErrAbortHandler {
				panic(v)
			}
			s.logger.Error("panic serving request", "method", r.Method, "path", r.URL.Path, "panic", v)
			writeError(w, http.StatusInternalServerError, "internal server error")
		}()
		next.ServeHTTP(w, r)
	})
}
