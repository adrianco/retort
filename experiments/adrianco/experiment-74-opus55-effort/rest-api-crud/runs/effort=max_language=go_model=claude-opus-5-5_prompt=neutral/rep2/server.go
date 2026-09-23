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
	"runtime/debug"
	"strconv"
	"strings"
	"time"
)

// maxBodyBytes caps request bodies; a book is a few hundred bytes of JSON.
const maxBodyBytes = 1 << 20

// healthCheckTimeout bounds how long GET /health waits for the database.
const healthCheckTimeout = 2 * time.Second

// Server is the HTTP API for the book collection.
type Server struct {
	store   *Store
	logger  *slog.Logger
	handler http.Handler
}

// NewServer returns the API, backed by store, as an http.Handler.
func NewServer(store *Store, logger *slog.Logger) *Server {
	s := &Server{store: store, logger: logger}
	s.handler = s.logRequests(s.recoverPanics(s.routes()))
	return s
}

// ServeHTTP implements http.Handler.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.handler.ServeHTTP(w, r)
}

func (s *Server) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.Handle("GET /books", s.handle(s.listBooks))
	mux.Handle("POST /books", s.handle(s.createBook))
	mux.Handle("GET /books/{id}", s.handle(s.getBook))
	mux.Handle("PUT /books/{id}", s.handle(s.updateBook))
	mux.Handle("DELETE /books/{id}", s.handle(s.deleteBook))

	// ServeMux's own 404 and 405 replies are plain text. These fallbacks keep
	// every response JSON; the method-specific patterns above take precedence.
	mux.Handle("/health", methodNotAllowed("GET, HEAD"))
	mux.Handle("/books", methodNotAllowed("GET, HEAD, POST"))
	mux.Handle("/books/{id}", methodNotAllowed("GET, HEAD, PUT, DELETE"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "not found")
	})
	return mux
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), healthCheckTimeout)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable,
			map[string]string{"status": "unavailable", "error": "database unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) error {
	books, err := s.store.ListBooks(r.Context(), strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		return err
	}
	writeJSON(w, http.StatusOK, books)
	return nil
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) error {
	in, err := readBookInput(w, r)
	if err != nil {
		return err
	}
	book, err := s.store.CreateBook(r.Context(), in)
	if err != nil {
		return err
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
	return nil
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) error {
	id, err := bookID(r)
	if err != nil {
		return err
	}
	book, err := s.store.GetBook(r.Context(), id)
	if err != nil {
		return err
	}
	writeJSON(w, http.StatusOK, book)
	return nil
}

// updateBook replaces a book. As when creating one, the body must be a
// complete book; optional fields that it omits are cleared.
func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) error {
	id, err := bookID(r)
	if err != nil {
		return err
	}
	// Look the book up before reading the body, so that a missing book is
	// reported as such whatever the request contains.
	if _, err := s.store.GetBook(r.Context(), id); err != nil {
		return err
	}
	in, err := readBookInput(w, r)
	if err != nil {
		return err
	}
	book, err := s.store.UpdateBook(r.Context(), id, in)
	if err != nil {
		return err
	}
	writeJSON(w, http.StatusOK, book)
	return nil
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) error {
	id, err := bookID(r)
	if err != nil {
		return err
	}
	if err := s.store.DeleteBook(r.Context(), id); err != nil {
		return err
	}
	w.WriteHeader(http.StatusNoContent)
	return nil
}

// bookID parses the {id} path segment. A value that is not a positive integer
// cannot identify a book, so it is reported as ErrNotFound.
func bookID(r *http.Request) (int64, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		return 0, ErrNotFound
	}
	return id, nil
}

// readBookInput decodes, normalizes and validates a book from the request body.
func readBookInput(w http.ResponseWriter, r *http.Request) (BookInput, error) {
	var in BookInput
	if err := decodeJSON(w, r, &in); err != nil {
		return BookInput{}, err
	}
	in.Normalize()
	if err := in.Validate(time.Now().Year()); err != nil {
		return BookInput{}, err
	}
	return in, nil
}

// handle adapts a handler that returns its error, sending the error to the
// client with respondError.
func (s *Server) handle(h func(http.ResponseWriter, *http.Request) error) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := h(w, r); err != nil {
			s.respondError(w, r, err)
		}
	})
}

// httpError is a client error whose message is safe to show to the client.
type httpError struct {
	status  int
	message string
}

func (e *httpError) Error() string { return e.message }

func badRequest(format string, args ...any) error {
	return &httpError{status: http.StatusBadRequest, message: fmt.Sprintf(format, args...)}
}

// errorResponse is the body of every error response.
type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

// respondError sends err as a JSON error response. Errors that mean nothing to
// the client are logged and reported as a bare 500, so that internal details
// do not leak.
func (s *Server) respondError(w http.ResponseWriter, r *http.Request, err error) {
	var (
		httpErr    *httpError
		invalidErr ValidationError
	)
	switch {
	case errors.As(err, &httpErr):
		writeError(w, httpErr.status, httpErr.message)
	case errors.As(err, &invalidErr):
		fields := make(map[string]string, len(invalidErr))
		for _, fe := range invalidErr {
			fields[fe.Field] = fe.Message
		}
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: invalidErr.Error(), Fields: fields})
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, ErrNotFound.Error())
	default:
		s.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "error", err)
		writeError(w, http.StatusInternalServerError, "internal server error")
	}
}

// methodNotAllowed answers requests for a known path with an unsupported method.
func methodNotAllowed(allow string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method "+r.Method+" not allowed")
	})
}

// decodeJSON reads a request body holding exactly one JSON value into dst.
// Fields that dst does not have are ignored.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) error {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(dst); err != nil {
		return describeDecodeError(err)
	}
	if err := dec.Decode(&json.RawMessage{}); !errors.Is(err, io.EOF) {
		if err == nil {
			return badRequest("request body must contain a single JSON object")
		}
		return describeDecodeError(err)
	}
	return nil
}

// describeDecodeError turns a JSON decoding error into a client error.
func describeDecodeError(err error) error {
	var (
		syntaxErr   *json.SyntaxError
		typeErr     *json.UnmarshalTypeError
		tooLargeErr *http.MaxBytesError
	)
	switch {
	case errors.Is(err, io.EOF):
		return badRequest("request body must not be empty")
	case errors.Is(err, io.ErrUnexpectedEOF) || errors.As(err, &syntaxErr):
		return badRequest("request body contains malformed JSON")
	case errors.As(err, &typeErr) && typeErr.Field != "":
		return badRequest("%s must be %s", typeErr.Field, jsonTypeName(typeErr.Type))
	case errors.As(err, &typeErr):
		return badRequest("request body must be a JSON object")
	case errors.As(err, &tooLargeErr):
		return &httpError{
			status:  http.StatusRequestEntityTooLarge,
			message: fmt.Sprintf("request body must not exceed %d bytes", tooLargeErr.Limit),
		}
	default:
		return badRequest("could not read request body")
	}
}

// jsonTypeName names the kind of JSON value that decodes into t.
func jsonTypeName(t reflect.Type) string {
	switch t.Kind() {
	case reflect.String:
		return "a string"
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return "an integer"
	case reflect.Float32, reflect.Float64:
		return "a number"
	case reflect.Bool:
		return "a boolean"
	case reflect.Slice, reflect.Array:
		return "an array"
	default:
		return "an object"
	}
}

// writeJSON sends v as a JSON response with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false) // keep titles such as "Pride & Prejudice" readable
	// The values sent here always encode, so an error means that the client has
	// gone away and there is no one left to tell.
	_ = enc.Encode(v)
}

// writeError sends a JSON error response.
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, errorResponse{Error: message})
}

// recoverPanics turns a panicking handler into a 500 response, where net/http
// would otherwise just drop the connection.
func (s *Server) recoverPanics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				s.logger.Error("panic serving request", "method", r.Method, "path", r.URL.Path,
					"panic", v, "stack", string(debug.Stack()))
				writeError(w, http.StatusInternalServerError, "internal server error")
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// logRequests logs the method, path, status and duration of every request.
func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.logger.Info("request", "method", r.Method, "path", r.URL.Path,
			"status", rec.status, "duration", time.Since(start))
	})
}

// statusRecorder remembers the status code that a handler sends.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}
