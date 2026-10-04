package main

import (
	"encoding/json"
	"errors"
	"fmt"
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

	maxTitleLen  = 500
	maxAuthorLen = 200
	maxISBNLen   = 32
	maxYear      = 9999
)

// Server exposes the book collection over HTTP.
type Server struct {
	store  *Store
	logger *slog.Logger
}

// NewServer returns a Server backed by store.
func NewServer(store *Store, logger *slog.Logger) *Server {
	return &Server{store: store, logger: logger}
}

// Routes returns the HTTP handler for the whole API.
func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreateBook)
	mux.HandleFunc("GET /books", s.handleListBooks)
	mux.HandleFunc("GET /books/{id}", s.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", s.handleDeleteBook)

	// Method-less patterns are less specific than the ones above, so they only
	// catch requests the API does not support and keep those errors in JSON.
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
	input, ok := readBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), input.book())
	if err != nil {
		s.internalError(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
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

func (s *Server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	input, ok := readBookInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, input.book())
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

// storeError maps an error from the store onto an HTTP response.
func (s *Server) storeError(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.internalError(w, r, err)
}

// internalError logs err and returns a generic 500 so internals never leak to
// the client.
func (s *Server) internalError(w http.ResponseWriter, r *http.Request, err error) {
	s.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "error", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// bookInput is the request body accepted by POST /books and PUT /books/{id}.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func (in *bookInput) normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// validate returns a message per invalid field, or nil if the input is valid.
func (in bookInput) validate() map[string]string {
	problems := map[string]string{}

	switch {
	case in.Title == "":
		problems["title"] = "title is required"
	case utf8.RuneCountInString(in.Title) > maxTitleLen:
		problems["title"] = fmt.Sprintf("title must be at most %d characters", maxTitleLen)
	}
	switch {
	case in.Author == "":
		problems["author"] = "author is required"
	case utf8.RuneCountInString(in.Author) > maxAuthorLen:
		problems["author"] = fmt.Sprintf("author must be at most %d characters", maxAuthorLen)
	}
	if in.Year < 0 || in.Year > maxYear {
		problems["year"] = fmt.Sprintf("year must be between 0 and %d", maxYear)
	}
	if utf8.RuneCountInString(in.ISBN) > maxISBNLen {
		problems["isbn"] = fmt.Sprintf("isbn must be at most %d characters", maxISBNLen)
	}

	if len(problems) == 0 {
		return nil
	}
	return problems
}

func (in bookInput) book() Book {
	return Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}

// readBookInput decodes and validates the request body. On failure it writes
// the error response itself and returns false.
func readBookInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var input bookInput
	if status, msg := decodeJSON(w, r, &input); status != 0 {
		writeError(w, status, msg)
		return bookInput{}, false
	}
	input.normalize()
	if problems := input.validate(); problems != nil {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Fields: problems})
		return bookInput{}, false
	}
	return input, true
}

// decodeJSON reads a single JSON value from the request body into dst. It
// returns a zero status on success, otherwise the status and message to send.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) (int, string) {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))

	if err := dec.Decode(dst); err != nil {
		var (
			syntaxErr   *json.SyntaxError
			typeErr     *json.UnmarshalTypeError
			maxBytesErr *http.MaxBytesError
		)
		switch {
		case errors.As(err, &maxBytesErr):
			return http.StatusRequestEntityTooLarge,
				fmt.Sprintf("request body must not exceed %d bytes", maxBodyBytes)
		case errors.Is(err, io.EOF):
			return http.StatusBadRequest, "request body must not be empty"
		case errors.As(err, &typeErr) && typeErr.Field != "":
			return http.StatusBadRequest,
				fmt.Sprintf("field %q has the wrong type (got JSON %s)", typeErr.Field, typeErr.Value)
		case errors.As(err, &typeErr):
			return http.StatusBadRequest, "request body must be a JSON object"
		case errors.As(err, &syntaxErr), errors.Is(err, io.ErrUnexpectedEOF):
			return http.StatusBadRequest, "request body contains malformed JSON"
		default:
			return http.StatusBadRequest, "request body could not be read"
		}
	}
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		return http.StatusBadRequest, "request body must contain a single JSON object"
	}
	return 0, ""
}

// parseID extracts the {id} path value. On failure it writes the error
// response itself and returns false.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	// The status line is already sent, so an encode failure (in practice a
	// client that went away) cannot be reported to the caller.
	_ = json.NewEncoder(w).Encode(v)
}

func methodNotAllowed(allow string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// statusRecorder captures the status code written by a handler.
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
