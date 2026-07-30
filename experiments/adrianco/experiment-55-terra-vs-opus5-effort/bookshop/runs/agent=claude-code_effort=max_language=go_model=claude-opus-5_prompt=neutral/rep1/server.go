package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"mime"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// maxRequestBytes caps request bodies. A book record is a few hundred bytes;
// 1 MiB is generous and still bounds what a single request can allocate.
const maxRequestBytes = 1 << 20

// Server routes HTTP requests to a Store.
type Server struct {
	store   *Store
	logger  *slog.Logger
	handler http.Handler
}

// NewServer builds the router and middleware chain. The result is an
// http.Handler and can be used directly with httptest.
func NewServer(store *Store, logger *slog.Logger) *Server {
	if logger == nil {
		logger = slog.New(slog.NewTextHandler(io.Discard, nil))
	}
	s := &Server{store: store, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreate)
	mux.HandleFunc("GET /books", s.handleList)
	mux.HandleFunc("GET /books/{id}", s.handleGet)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	mux.HandleFunc("DELETE /books/{id}", s.handleDelete)

	// Method-less patterns are strictly less specific than the ones above, so
	// they only catch requests that used the wrong verb on a real path. Without
	// them ServeMux would answer 405 with a plain-text body.
	mux.HandleFunc("/health", methodNotAllowed(http.MethodGet))
	mux.HandleFunc("/books", methodNotAllowed(http.MethodGet, http.MethodPost))
	mux.HandleFunc("/books/{id}", methodNotAllowed(http.MethodGet, http.MethodPut, http.MethodDelete))

	// Everything else, so unknown paths get a JSON 404 too.
	mux.HandleFunc("/", handleUnknownRoute)

	s.handler = recoverPanics(s.logger, logRequests(s.logger, mux))
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.handler.ServeHTTP(w, r)
}

// --- handlers ---------------------------------------------------------------

type healthResponse struct {
	Status   string `json:"status"`
	Database string `json:"database"`
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, healthResponse{Status: "unavailable", Database: "down"})
		return
	}
	writeJSON(w, http.StatusOK, healthResponse{Status: "ok", Database: "up"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, err := decodeInput(w, r)
	if err != nil {
		s.fail(w, r, err)
		return
	}

	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.fail(w, r, err)
		return
	}

	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))

	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		s.fail(w, r, err)
		return
	}

	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	in, err := decodeInput(w, r)
	if err != nil {
		s.fail(w, r, err)
		return
	}

	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r)
	if err != nil {
		s.fail(w, r, err)
		return
	}

	if err := s.store.Delete(r.Context(), id); err != nil {
		s.fail(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func handleUnknownRoute(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusNotFound, fmt.Sprintf("no route for %s %s", r.Method, r.URL.Path))
}

func methodNotAllowed(allowed ...string) http.HandlerFunc {
	allow := strings.Join(allowed, ", ")
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed,
			fmt.Sprintf("method %s is not allowed on %s", r.Method, r.URL.Path),
			"allowed methods: "+allow)
	}
}

// --- request decoding -------------------------------------------------------

// decodeInput reads, cleans and validates a book payload, returning an error
// already carrying the right HTTP status.
func decodeInput(w http.ResponseWriter, r *http.Request) (BookInput, error) {
	var in BookInput
	if err := decodeJSON(w, r, &in); err != nil {
		return BookInput{}, err
	}
	in.Clean()
	if err := in.Validate(time.Now()); err != nil {
		return BookInput{}, err
	}
	return in, nil
}

func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) error {
	// An explicit Content-Type must be JSON; a missing one is tolerated so
	// that a bare `curl -d` still works.
	if ct := r.Header.Get("Content-Type"); ct != "" {
		mediaType, _, err := mime.ParseMediaType(ct)
		if err != nil || mediaType != "application/json" {
			return &httpError{
				status:  http.StatusUnsupportedMediaType,
				message: "request body must be application/json",
			}
		}
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxRequestBytes)
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(dst); err != nil {
		return decodeError(err)
	}
	// Reject trailing content so `{"title":"a"}{"title":"b"}` is not silently
	// read as just the first object.
	if dec.More() {
		return &httpError{status: http.StatusBadRequest, message: "request body must contain a single JSON object"}
	}
	return nil
}

func decodeError(err error) error {
	var (
		syntaxErr   *json.SyntaxError
		typeErr     *json.UnmarshalTypeError
		maxBytesErr *http.MaxBytesError
	)
	switch {
	case errors.As(err, &maxBytesErr):
		return &httpError{
			status:  http.StatusRequestEntityTooLarge,
			message: fmt.Sprintf("request body must not exceed %d bytes", maxRequestBytes),
		}
	case errors.As(err, &syntaxErr):
		return &httpError{
			status:  http.StatusBadRequest,
			message: fmt.Sprintf("request body contains malformed JSON at byte %d", syntaxErr.Offset),
		}
	case errors.As(err, &typeErr):
		return &httpError{
			status:  http.StatusBadRequest,
			message: fmt.Sprintf("field %q must be of type %s", typeErr.Field, typeErr.Type),
		}
	case errors.Is(err, io.EOF), errors.Is(err, io.ErrUnexpectedEOF):
		return &httpError{status: http.StatusBadRequest, message: "request body must contain a JSON object"}
	default:
		return &httpError{status: http.StatusBadRequest, message: "request body could not be parsed as JSON"}
	}
}

func parseID(r *http.Request) (int64, error) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id <= 0 {
		return 0, &httpError{
			status:  http.StatusBadRequest,
			message: fmt.Sprintf("invalid book id %q: must be a positive integer", raw),
		}
	}
	return id, nil
}

// --- responses --------------------------------------------------------------

// httpError is an error that already knows which status code it deserves.
type httpError struct {
	status  int
	message string
	details []string
}

func (e *httpError) Error() string { return e.message }

type errorResponse struct {
	Error   string   `json:"error"`
	Details []string `json:"details,omitempty"`
}

// fail translates an error from any layer into the matching HTTP response.
// Anything unrecognised is logged and reported as a 500 without leaking
// internals to the client.
func (s *Server) fail(w http.ResponseWriter, r *http.Request, err error) {
	var (
		httpErr *httpError
		valErr  *ValidationError
	)
	switch {
	case errors.As(err, &httpErr):
		writeError(w, httpErr.status, httpErr.message, httpErr.details...)
	case errors.As(err, &valErr):
		writeError(w, http.StatusBadRequest, "validation failed", valErr.Problems...)
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, ErrNotFound.Error())
	case errors.Is(err, ErrDuplicateISBN):
		writeError(w, http.StatusConflict, ErrDuplicateISBN.Error())
	default:
		s.logger.Error("request failed",
			"method", r.Method, "path", r.URL.Path, "err", err)
		writeError(w, http.StatusInternalServerError, "internal server error")
	}
}

func writeError(w http.ResponseWriter, status int, message string, details ...string) {
	writeJSON(w, status, errorResponse{Error: message, Details: details})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	// Marshal first: an encoding failure here must not leave a half-written
	// body behind a 200.
	body, err := json.Marshal(payload)
	if err != nil {
		http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	_, _ = w.Write(append(body, '\n'))
}

// --- middleware -------------------------------------------------------------

func logRequests(logger *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		logger.Info("request",
			"method", r.Method,
			"path", r.URL.Path,
			"query", r.URL.RawQuery,
			"status", rec.status,
			"bytes", rec.written,
			"duration", time.Since(start).String(),
		)
	})
}

func recoverPanics(logger *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				// A panic after the handler already started writing cannot be
				// turned into a clean 500, but it must not kill the process.
				if v == http.ErrAbortHandler {
					panic(v)
				}
				logger.Error("panic recovered", "method", r.Method, "path", r.URL.Path, "panic", v)
				writeError(w, http.StatusInternalServerError, "internal server error")
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// statusRecorder remembers the status code and size for the access log.
type statusRecorder struct {
	http.ResponseWriter
	status  int
	written int
	wrote   bool
}

func (r *statusRecorder) WriteHeader(status int) {
	if !r.wrote {
		r.status, r.wrote = status, true
	}
	r.ResponseWriter.WriteHeader(status)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	r.wrote = true
	n, err := r.ResponseWriter.Write(b)
	r.written += n
	return n, err
}

// Unwrap lets http.ResponseController reach the underlying ResponseWriter.
func (r *statusRecorder) Unwrap() http.ResponseWriter { return r.ResponseWriter }
