package main

import (
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxBodyBytes = 1 << 20 // 1 MiB
	maxTextLen   = 500
	maxISBNLen   = 32
	maxYear      = 9999
)

// Server exposes the book collection over HTTP.
type Server struct {
	store  *Store
	logger *slog.Logger
}

// NewServer returns the HTTP handler for the book API.
func NewServer(store *Store, logger *slog.Logger) http.Handler {
	s := &Server{store: store, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreateBook)
	mux.HandleFunc("GET /books", s.handleListBooks)
	mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)

	// Method-less fallbacks so that unsupported methods and unknown paths get
	// JSON errors instead of the mux's plain-text defaults.
	mux.HandleFunc("/health", methodNotAllowed("GET, HEAD"))
	mux.HandleFunc("/books", methodNotAllowed("GET, HEAD, POST"))
	mux.HandleFunc("/books/{id}", methodNotAllowed("GET, HEAD, PUT, DELETE"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "resource not found")
	})

	return s.logRequests(mux)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		s.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
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
		s.internalError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
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
	in, ok := s.readBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.storeError(w, err)
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
		s.storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// readBookInput decodes and validates a book from the request body. On failure
// it writes the error response and returns false.
func (s *Server) readBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput

	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(&in); err != nil {
		writeDecodeError(w, err)
		return BookInput{}, false
	}
	if err := dec.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return BookInput{}, false
	}

	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	if fields := validateBook(in); len(fields) > 0 {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Fields: fields})
		return BookInput{}, false
	}
	return in, true
}

// validateBook returns a message per invalid field, or an empty map if the
// input is valid. Title and author are required; year and isbn are optional.
func validateBook(in BookInput) map[string]string {
	fields := map[string]string{}

	switch {
	case in.Title == "":
		fields["title"] = "title is required"
	case utf8.RuneCountInString(in.Title) > maxTextLen:
		fields["title"] = "title must be at most " + strconv.Itoa(maxTextLen) + " characters"
	}

	switch {
	case in.Author == "":
		fields["author"] = "author is required"
	case utf8.RuneCountInString(in.Author) > maxTextLen:
		fields["author"] = "author must be at most " + strconv.Itoa(maxTextLen) + " characters"
	}

	if in.Year < 0 || in.Year > maxYear {
		fields["year"] = "year must be between 0 and " + strconv.Itoa(maxYear)
	}

	if utf8.RuneCountInString(in.ISBN) > maxISBNLen {
		fields["isbn"] = "isbn must be at most " + strconv.Itoa(maxISBNLen) + " characters"
	}

	return fields
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

func (s *Server) storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.internalError(w, err)
}

func (s *Server) internalError(w http.ResponseWriter, err error) {
	s.logger.Error("request failed", "error", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func methodNotAllowed(allow string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeDecodeError(w http.ResponseWriter, err error) {
	var tooLarge *http.MaxBytesError
	var typeErr *json.UnmarshalTypeError
	switch {
	case errors.As(err, &tooLarge):
		writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "request body is empty")
	case errors.As(err, &typeErr) && typeErr.Field != "":
		writeError(w, http.StatusBadRequest, "invalid type for field "+strconv.Quote(typeErr.Field))
	case errors.As(err, &typeErr):
		writeError(w, http.StatusBadRequest, "request body must be a JSON object")
	default:
		writeError(w, http.StatusBadRequest, "request body is not valid JSON")
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
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
