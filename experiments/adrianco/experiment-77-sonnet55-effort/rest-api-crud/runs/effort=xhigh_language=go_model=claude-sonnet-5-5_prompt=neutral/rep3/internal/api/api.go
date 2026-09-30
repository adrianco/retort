// Package api implements the HTTP interface of the book service.
package api

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

	"bookapi/internal/book"
)

const (
	maxBodyBytes = 1 << 20 // 1 MiB
	pingTimeout  = 2 * time.Second
)

// BookStore is the persistence behaviour the handlers depend on.
type BookStore interface {
	Create(ctx context.Context, in book.Input) (book.Book, error)
	List(ctx context.Context, author string) ([]book.Book, error)
	Get(ctx context.Context, id int64) (book.Book, error)
	Update(ctx context.Context, id int64, in book.Input) (book.Book, error)
	Delete(ctx context.Context, id int64) error
	Ping(ctx context.Context) error
}

type handler struct {
	store  BookStore
	logger *slog.Logger
}

// New returns the service's HTTP handler, with request logging and panic
// recovery applied. A nil logger discards logs.
func New(store BookStore, logger *slog.Logger) http.Handler {
	if logger == nil {
		logger = slog.New(slog.DiscardHandler)
	}
	h := &handler{store: store, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("/health", methodNotAllowed(http.MethodGet))

	mux.HandleFunc("POST /books", h.createBook)
	mux.HandleFunc("GET /books", h.listBooks)
	mux.HandleFunc("/books", methodNotAllowed(http.MethodGet, http.MethodPost))

	mux.HandleFunc("GET /books/{id}", h.getBook)
	mux.HandleFunc("PUT /books/{id}", h.updateBook)
	mux.HandleFunc("DELETE /books/{id}", h.deleteBook)
	mux.HandleFunc("/books/{id}", methodNotAllowed(http.MethodGet, http.MethodPut, http.MethodDelete))

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "not found")
	})

	return middleware(logger, mux)
}

func (h *handler) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), pingTimeout)
	defer cancel()
	if err := h.store.Ping(ctx); err != nil {
		h.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *handler) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := readInput(w, r)
	if !ok {
		return
	}
	b, err := h.store.Create(r.Context(), in)
	if err != nil {
		h.internalError(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (h *handler) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := h.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		h.internalError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (h *handler) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := h.store.Get(r.Context(), id)
	if err != nil {
		h.storeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handler) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	in, ok := readInput(w, r)
	if !ok {
		return
	}
	b, err := h.store.Update(r.Context(), id, in)
	if err != nil {
		h.storeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handler) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := h.store.Delete(r.Context(), id); err != nil {
		h.storeError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// storeError maps a store failure to a response: 404 for a missing book,
// otherwise 500.
func (h *handler) storeError(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, book.ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	h.internalError(w, r, err)
}

// internalError logs the real cause but never exposes it to the client.
func (h *handler) internalError(w http.ResponseWriter, r *http.Request, err error) {
	h.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "err", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// pathID parses the {id} path segment, writing a 400 response on failure.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

// readInput decodes and validates a book from the request body, writing an
// error response and returning false if it is unacceptable.
func readInput(w http.ResponseWriter, r *http.Request) (book.Input, bool) {
	var in book.Input
	if status, msg := decodeJSON(w, r, &in); status != 0 {
		writeError(w, status, msg)
		return book.Input{}, false
	}
	clean, err := in.Clean()
	if err != nil {
		var verr book.ValidationError
		if errors.As(err, &verr) {
			writeJSON(w, http.StatusBadRequest, errorBody{Error: "validation failed", Details: verr})
		} else {
			writeError(w, http.StatusBadRequest, err.Error())
		}
		return book.Input{}, false
	}
	return clean, true
}

// decodeJSON reads exactly one JSON value from the body into dst. On failure
// it returns the HTTP status and message to report; on success the status is 0.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) (int, string) {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	err := dec.Decode(dst)
	if err == nil {
		// Anything after the first value (other than whitespace) is an error.
		if _, extra := dec.Token(); extra != io.EOF {
			if isTooLarge(extra) {
				return http.StatusRequestEntityTooLarge, "request body too large"
			}
			return http.StatusBadRequest, "request body must contain a single JSON object"
		}
		return 0, ""
	}

	var (
		syntaxErr *json.SyntaxError
		typeErr   *json.UnmarshalTypeError
	)
	switch {
	case isTooLarge(err):
		return http.StatusRequestEntityTooLarge, "request body too large"
	case errors.Is(err, io.EOF):
		return http.StatusBadRequest, "request body must not be empty"
	case errors.As(err, &typeErr):
		if typeErr.Field != "" {
			return http.StatusBadRequest, fmt.Sprintf("field %q must be a JSON %s", typeErr.Field, jsonKind(typeErr.Type))
		}
		return http.StatusBadRequest, "request body must be a JSON object"
	case errors.As(err, &syntaxErr), errors.Is(err, io.ErrUnexpectedEOF):
		return http.StatusBadRequest, "request body is not valid JSON"
	default:
		return http.StatusBadRequest, "request body could not be read"
	}
}

func isTooLarge(err error) bool {
	var tooLarge *http.MaxBytesError
	return errors.As(err, &tooLarge)
}

// jsonKind names the JSON type a Go type is decoded from, for error messages.
func jsonKind(t reflect.Type) string {
	switch t.Kind() {
	case reflect.String:
		return "string"
	case reflect.Int, reflect.Int64:
		return "integer"
	default:
		return "value"
	}
}
