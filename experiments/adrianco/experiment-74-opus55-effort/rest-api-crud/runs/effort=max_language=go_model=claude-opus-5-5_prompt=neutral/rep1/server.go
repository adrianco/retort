package main

import (
	"bytes"
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

// maxBodyBytes is the largest request body the API accepts.
const maxBodyBytes = 1 << 20 // 1 MiB

// Server serves the book collection's REST API.
type Server struct {
	store  *Store
	logger *slog.Logger
}

// NewServer returns a Server that keeps books in store and logs to logger.
func NewServer(store *Store, logger *slog.Logger) *Server {
	return &Server{store: store, logger: logger}
}

// Handler returns the http.Handler for the whole API.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.Handle("GET /health", s.handle(s.health))
	mux.Handle("GET /books", s.handle(s.listBooks))
	mux.Handle("POST /books", s.handle(s.createBook))
	mux.Handle("GET /books/{id}", s.handle(s.getBook))
	mux.Handle("PUT /books/{id}", s.handle(s.updateBook))
	mux.Handle("DELETE /books/{id}", s.handle(s.deleteBook))

	// Left to itself, ServeMux answers unsupported methods and unknown paths
	// in plain text. These patterns are less specific than the ones above, so
	// they only get the requests those turn away, and answer them in JSON.
	mux.Handle("/health", s.methodNotAllowed("GET, HEAD"))
	mux.Handle("/books", s.methodNotAllowed("GET, HEAD, POST"))
	mux.Handle("/books/{id}", s.methodNotAllowed("GET, HEAD, PUT, DELETE"))
	mux.Handle("/", s.handle(func(http.ResponseWriter, *http.Request) error {
		return &apiError{status: http.StatusNotFound, message: "not found"}
	}))

	return s.logRequests(s.recoverPanics(mux))
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) error {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.ErrorContext(ctx, "health check failed", "err", err)
		s.writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return nil
	}
	s.writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	return nil
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) error {
	books, err := s.store.List(r.Context(), strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		return err
	}
	s.writeJSON(w, http.StatusOK, books)
	return nil
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) error {
	book, err := readBook(w, r)
	if err != nil {
		return err
	}
	created, err := s.store.Create(r.Context(), book)
	if err != nil {
		return err
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	s.writeJSON(w, http.StatusCreated, created)
	return nil
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) error {
	id, err := bookID(r)
	if err != nil {
		return err
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		return err
	}
	s.writeJSON(w, http.StatusOK, book)
	return nil
}

// updateBook replaces a book: like POST, it takes the complete book, and
// optional fields that are left out are cleared.
func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) error {
	id, err := bookID(r)
	if err != nil {
		return err
	}
	book, err := readBook(w, r)
	if err != nil {
		return err
	}
	book.ID = id
	updated, err := s.store.Update(r.Context(), book)
	if err != nil {
		return err
	}
	s.writeJSON(w, http.StatusOK, updated)
	return nil
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) error {
	id, err := bookID(r)
	if err != nil {
		return err
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		return err
	}
	w.WriteHeader(http.StatusNoContent)
	return nil
}

// methodNotAllowed answers 405 Method Not Allowed, listing the allowed methods.
func (s *Server) methodNotAllowed(allow string) http.Handler {
	return s.handle(func(w http.ResponseWriter, r *http.Request) error {
		w.Header().Set("Allow", allow)
		return &apiError{status: http.StatusMethodNotAllowed, message: "method " + r.Method + " not allowed"}
	})
}

// bookID parses the {id} path segment.
func bookID(r *http.Request) (int64, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		return 0, badRequest("book id must be a positive integer")
	}
	return id, nil
}

// readBook decodes and validates the book in the request body.
func readBook(w http.ResponseWriter, r *http.Request) (Book, error) {
	var in BookInput
	if err := decodeJSON(w, r, &in); err != nil {
		return Book{}, err
	}
	// Next year is allowed for forthcoming titles, and for clients in time
	// zones where it has already begun.
	book, fieldErrs := in.Validate(time.Now().Year() + 1)
	if fieldErrs != nil {
		return Book{}, &apiError{status: http.StatusBadRequest, message: "validation failed", fields: fieldErrs}
	}
	return book, nil
}

// decodeJSON reads the request body, which must hold a single JSON value, into
// dst. Any problem with the body is returned as an *apiError.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) error {
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	var sizeErr *http.MaxBytesError
	switch {
	case errors.As(err, &sizeErr):
		return &apiError{
			status:  http.StatusRequestEntityTooLarge,
			message: fmt.Sprintf("request body must not be larger than %d bytes", sizeErr.Limit),
		}
	case err != nil:
		return badRequest("could not read request body")
	case len(bytes.TrimSpace(body)) == 0:
		return badRequest("request body is empty")
	}

	err = json.Unmarshal(body, dst)
	var typeErr *json.UnmarshalTypeError
	switch {
	case err == nil:
		return nil
	case errors.As(err, &typeErr) && typeErr.Field != "":
		return &apiError{
			status:  http.StatusBadRequest,
			message: "validation failed",
			fields:  FieldErrors{typeErr.Field: "must be " + jsonTypeName(typeErr.Type)},
		}
	case errors.As(err, &typeErr):
		return badRequest("request body must be a JSON object")
	default:
		return badRequest("request body is not valid JSON")
	}
}

// jsonTypeName names the kind of JSON value that decodes into a Go type.
func jsonTypeName(t reflect.Type) string {
	switch t.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return "an integer"
	case reflect.String:
		return "a string"
	default:
		return "a JSON value of type " + t.String()
	}
}

// apiError is an error that is reported to the client with its own status.
type apiError struct {
	status  int
	message string
	fields  FieldErrors
}

func (e *apiError) Error() string { return e.message }

func badRequest(message string) *apiError {
	return &apiError{status: http.StatusBadRequest, message: message}
}

// errorResponse is the body of every error response. Fields is present only
// for invalid input, and says what is wrong with each offending field.
type errorResponse struct {
	Error  string      `json:"error"`
	Fields FieldErrors `json:"fields,omitempty"`
}

// handlerFunc is an HTTP handler that may fail. If it returns an error it
// must not have written a response.
type handlerFunc func(w http.ResponseWriter, r *http.Request) error

// handle adapts h to an http.Handler that reports h's error as a JSON error
// response. Errors other than *apiError and ErrNotFound are unexpected: they
// are logged, and the client is told only that there was an internal error.
func (s *Server) handle(h handlerFunc) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		err := h(w, r)
		if err == nil {
			return
		}
		var apiErr *apiError
		switch {
		case errors.As(err, &apiErr):
			s.writeJSON(w, apiErr.status, errorResponse{Error: apiErr.message, Fields: apiErr.fields})
		case errors.Is(err, ErrNotFound):
			s.writeJSON(w, http.StatusNotFound, errorResponse{Error: ErrNotFound.Error()})
		default:
			s.logger.ErrorContext(r.Context(), "request failed",
				"method", r.Method, "path", r.URL.Path, "err", err)
			s.writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "internal server error"})
		}
	})
}

// writeJSON sends v as the JSON response body with the given status code.
func (s *Server) writeJSON(w http.ResponseWriter, status int, v any) {
	body, err := json.Marshal(v)
	if err != nil {
		s.logger.Error("encoding response", "err", err)
		status, body = http.StatusInternalServerError, []byte(`{"error":"internal server error"}`)
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(append(body, '\n')) // an error means the client has gone
}

// logRequests logs the method, path, response status and duration of every
// request.
func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(sw, r)
		s.logger.InfoContext(r.Context(), "request",
			"method", r.Method, "path", r.URL.Path, "status", sw.status, "duration", time.Since(start))
	})
}

// recoverPanics answers a request whose handler panics with a 500 response,
// instead of the dropped connection net/http would otherwise leave the
// client with.
func (s *Server) recoverPanics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			v := recover()
			if v == nil {
				return
			}
			if v == http.ErrAbortHandler {
				panic(v) // a deliberate abort, which net/http handles quietly
			}
			s.logger.ErrorContext(r.Context(), "panic serving request",
				"method", r.Method, "path", r.URL.Path, "panic", v, "stack", string(debug.Stack()))
			s.writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "internal server error"})
		}()
		next.ServeHTTP(w, r)
	})
}

// statusWriter is an http.ResponseWriter that remembers the status it sent.
type statusWriter struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (w *statusWriter) WriteHeader(status int) {
	if !w.wroteHeader {
		w.status, w.wroteHeader = status, true
	}
	w.ResponseWriter.WriteHeader(status)
}

func (w *statusWriter) Write(b []byte) (int, error) {
	w.wroteHeader = true
	return w.ResponseWriter.Write(b)
}

// Unwrap lets http.ResponseController reach the underlying ResponseWriter.
func (w *statusWriter) Unwrap() http.ResponseWriter { return w.ResponseWriter }
