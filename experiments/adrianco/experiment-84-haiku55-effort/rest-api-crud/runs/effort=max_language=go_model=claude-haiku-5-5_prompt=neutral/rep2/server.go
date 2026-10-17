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
	"strings"
	"time"
)

// maxBodyBytes caps the size of a request body.
const maxBodyBytes = 1 << 20

// errTrailingData means a request body held more than one JSON value.
var errTrailingData = errors.New("request body must contain a single JSON object")

// Server serves the book collection API over HTTP.
type Server struct {
	store  *Store
	logger *slog.Logger
}

// NewServer returns a Server that reads and writes books through store.
func NewServer(store *Store, logger *slog.Logger) *Server {
	return &Server{store: store, logger: logger}
}

// Handler returns the API's HTTP handler, with request logging applied.
//
// Routes are matched by path and dispatched on method inside each handler, so
// that unsupported methods and unknown paths also get JSON error bodies.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", s.handleHealth)
	mux.HandleFunc("/books", s.handleBooks)
	mux.HandleFunc("/books/{id}", s.handleBook)
	mux.HandleFunc("/", s.handleNotFound)
	return s.logRequests(mux)
}

func (s *Server) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet, http.MethodHead:
		s.listBooks(w, r)
	case http.MethodPost:
		s.createBook(w, r)
	default:
		writeMethodNotAllowed(w, http.MethodGet, http.MethodHead, http.MethodPost)
	}
}

func (s *Server) handleBook(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet, http.MethodHead:
		s.getBook(w, r)
	case http.MethodPut:
		s.updateBook(w, r)
	case http.MethodDelete:
		s.deleteBook(w, r)
	default:
		writeMethodNotAllowed(w, http.MethodGet, http.MethodHead, http.MethodPut, http.MethodDelete)
	}
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		writeMethodNotAllowed(w, http.MethodGet, http.MethodHead)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleNotFound(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusNotFound, "not found")
}

// listBooks answers GET /books, optionally filtered by ?author=.
func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

// createBook answers POST /books.
func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	book, ok := readBook(w, r)
	if !ok {
		return
	}
	created, err := s.store.Create(r.Context(), book)
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", created.ID))
	writeJSON(w, http.StatusCreated, created)
}

// getBook answers GET /books/{id}.
func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
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

// updateBook answers PUT /books/{id}. The body replaces the whole book, so
// title and author are required and an omitted year or ISBN is cleared.
func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	book, ok := readBook(w, r)
	if !ok {
		return
	}
	updated, err := s.store.Update(r.Context(), id, book)
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

// deleteBook answers DELETE /books/{id}.
func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := bookID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// writeStoreError maps a failed store call to an HTTP error response.
func (s *Server) writeStoreError(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, ErrNotFound.Error())
		return
	}
	s.logger.Error("store operation failed", "method", r.Method, "path", r.URL.Path, "error", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// logRequests logs the method, path, status and duration of every request.
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

// statusRecorder remembers the status code a handler wrote.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

// bookID parses the {id} path segment. It writes a 400 response and returns
// false if the segment is not an integer.
func bookID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "book id must be an integer")
		return 0, false
	}
	return id, true
}

// readBook decodes, normalizes and validates the book in the request body. On
// failure it writes the error response and returns false.
func readBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	var book Book
	if err := decodeSingleJSON(r.Body, &book); err != nil {
		writeBodyError(w, err)
		return Book{}, false
	}
	book.normalize()
	if fields := book.validate(latestPublicationYear()); fields != nil {
		writeValidationError(w, fields)
		return Book{}, false
	}
	return book, true
}

// decodeSingleJSON decodes exactly one JSON value from r into v. Unknown
// object fields are ignored.
func decodeSingleJSON(r io.Reader, v any) error {
	dec := json.NewDecoder(r)
	if err := dec.Decode(v); err != nil {
		return err
	}
	// Only whitespace may follow the value. Any other error, such as the body
	// exceeding its size limit, is reported as it is.
	if err := dec.Decode(&struct{}{}); err != io.EOF {
		if err == nil {
			return errTrailingData
		}
		return err
	}
	return nil
}

// writeBodyError describes why a request body could not be decoded.
func writeBodyError(w http.ResponseWriter, err error) {
	var tooLarge *http.MaxBytesError
	var typeErr *json.UnmarshalTypeError
	switch {
	case errors.As(err, &tooLarge):
		writeError(w, http.StatusRequestEntityTooLarge, fmt.Sprintf("request body must be at most %d bytes", maxBodyBytes))
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "request body is required")
	case errors.Is(err, errTrailingData):
		writeError(w, http.StatusBadRequest, errTrailingData.Error())
	case errors.As(err, &typeErr) && typeErr.Field != "":
		writeValidationError(w, fieldErrors{typeErr.Field: wrongTypeMessage(typeErr)})
	case errors.As(err, &typeErr):
		writeError(w, http.StatusBadRequest, "request body must be a JSON object")
	default:
		writeError(w, http.StatusBadRequest, "malformed JSON: "+err.Error())
	}
}

// wrongTypeMessage describes the type a field should have had.
func wrongTypeMessage(e *json.UnmarshalTypeError) string {
	switch e.Type.Kind() {
	case reflect.Int:
		return "must be an integer"
	case reflect.String:
		return "must be a string"
	}
	return "has the wrong type"
}

// errorResponse is the body of every error response.
type errorResponse struct {
	Error  string      `json:"error"`
	Fields fieldErrors `json:"fields,omitempty"`
}

func writeValidationError(w http.ResponseWriter, fields fieldErrors) {
	writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Fields: fields})
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func writeMethodNotAllowed(w http.ResponseWriter, allowed ...string) {
	w.Header().Set("Allow", strings.Join(allowed, ", "))
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	// The status line has already been sent, so an encoding failure has no
	// useful response to fall back to.
	_ = json.NewEncoder(w).Encode(v)
}
