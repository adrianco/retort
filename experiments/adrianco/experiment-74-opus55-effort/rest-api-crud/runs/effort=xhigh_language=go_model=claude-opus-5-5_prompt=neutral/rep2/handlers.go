package main

import (
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

// maxBodyBytes caps the size of request bodies.
const maxBodyBytes = 1 << 20

// Server exposes the book store over HTTP.
type Server struct {
	store  *Store
	logger *slog.Logger
	now    func() time.Time
}

// NewServer returns an http.Handler serving the book API backed by store.
func NewServer(store *Store, logger *slog.Logger) http.Handler {
	s := &Server{store: store, logger: logger, now: time.Now}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreateBook)
	mux.HandleFunc("GET /books", s.handleListBooks)
	mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)
	return s.logRequests(mux)
}

type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		s.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	book, ok := s.readBook(w, r)
	if !ok {
		return
	}
	created, err := s.store.Create(r.Context(), book)
	if err != nil {
		s.internalError(w, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", created.ID))
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		s.internalError(w, err)
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
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, ok := s.readBook(w, r)
	if !ok {
		return
	}
	updated, err := s.store.Update(r.Context(), id, book)
	if err != nil {
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// readBook decodes and validates a BookInput from the request body. On
// failure it writes an error response and returns ok=false.
func (s *Server) readBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var in BookInput
	if status, resp := decodeJSON(w, r, &in); resp != nil {
		writeJSON(w, status, resp)
		return Book{}, false
	}
	book, fieldErrs := in.Validate(s.now())
	if fieldErrs != nil {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Fields: fieldErrs})
		return Book{}, false
	}
	return book, true
}

// decodeJSON reads a single JSON object from the request body into dst. On
// failure it returns the status code and error body to send to the client.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) (int, *errorResponse) {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))

	err := dec.Decode(dst)
	var (
		syntaxErr  *json.SyntaxError
		typeErr    *json.UnmarshalTypeError
		maxSizeErr *http.MaxBytesError
	)
	switch {
	case err == nil:
	case errors.Is(err, io.EOF):
		return http.StatusBadRequest, &errorResponse{Error: "request body is required"}
	case errors.As(err, &syntaxErr):
		return http.StatusBadRequest, &errorResponse{Error: fmt.Sprintf("malformed JSON at offset %d", syntaxErr.Offset)}
	case errors.Is(err, io.ErrUnexpectedEOF):
		return http.StatusBadRequest, &errorResponse{Error: "malformed JSON: unexpected end of input"}
	case errors.As(err, &typeErr):
		if typeErr.Field == "" {
			return http.StatusBadRequest, &errorResponse{Error: "request body must be a JSON object"}
		}
		return http.StatusBadRequest, &errorResponse{
			Error:  "validation failed",
			Fields: map[string]string{typeErr.Field: "must be " + jsonTypeName(typeErr.Type)},
		}
	case errors.As(err, &maxSizeErr):
		return http.StatusRequestEntityTooLarge, &errorResponse{
			Error: fmt.Sprintf("request body must not exceed %d bytes", maxSizeErr.Limit),
		}
	default:
		return http.StatusBadRequest, &errorResponse{Error: "invalid JSON: " + err.Error()}
	}

	if err := dec.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return http.StatusBadRequest, &errorResponse{Error: "request body must contain a single JSON object"}
	}
	return 0, nil
}

func jsonTypeName(t reflect.Type) string {
	switch t.Kind() {
	case reflect.String:
		return "a string"
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return "an integer"
	default:
		return "a valid " + t.Kind().String()
	}
}

// parseID extracts the positive integer {id} path value. On failure it writes
// a 400 response and returns ok=false.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "book id must be a positive integer"})
		return 0, false
	}
	return id, true
}

func (s *Server) storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeJSON(w, http.StatusNotFound, errorResponse{Error: ErrNotFound.Error()})
		return
	}
	s.internalError(w, err)
}

func (s *Server) internalError(w http.ResponseWriter, err error) {
	s.logger.Error("internal error", "err", err)
	writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "internal server error"})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// The status line is already sent, so an encode failure (typically a
	// client disconnect) cannot be reported to the client.
	_ = json.NewEncoder(w).Encode(v)
}

// statusRecorder captures the response status for request logging.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (rec *statusRecorder) WriteHeader(code int) {
	rec.status = code
	rec.ResponseWriter.WriteHeader(code)
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
			"duration", time.Since(start))
	})
}
