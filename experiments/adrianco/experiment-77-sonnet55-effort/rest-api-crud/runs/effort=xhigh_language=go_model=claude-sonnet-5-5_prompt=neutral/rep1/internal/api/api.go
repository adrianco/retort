// Package api exposes the book store over HTTP.
package api

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"

	"bookapi/internal/books"
)

// maxBodyBytes caps request bodies; a book is a few hundred bytes.
const maxBodyBytes = 1 << 20

// Store is the persistence the handlers need.
type Store interface {
	Ping(ctx context.Context) error
	Create(ctx context.Context, in books.Input) (books.Book, error)
	Get(ctx context.Context, id int64) (books.Book, error)
	List(ctx context.Context, author string) ([]books.Book, error)
	Update(ctx context.Context, id int64, in books.Input) (books.Book, error)
	Delete(ctx context.Context, id int64) error
}

type handler struct {
	store  Store
	logger *slog.Logger
}

// New returns the service's HTTP handler. A nil logger discards logs.
func New(store Store, logger *slog.Logger) http.Handler {
	if logger == nil {
		logger = slog.New(slog.DiscardHandler)
	}
	h := &handler{store: store, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("POST /books", h.create)
	mux.HandleFunc("GET /books", h.list)
	mux.HandleFunc("GET /books/{id}", h.get)
	mux.HandleFunc("PUT /books/{id}", h.update)
	mux.HandleFunc("DELETE /books/{id}", h.delete)

	// Method-less patterns lose to the ones above, so they only see the
	// remaining methods and let us answer 405/404 in JSON like everything else.
	mux.HandleFunc("/health", methodNotAllowed("GET"))
	mux.HandleFunc("/books", methodNotAllowed("GET", "POST"))
	mux.HandleFunc("/books/{id}", methodNotAllowed("GET", "PUT", "DELETE"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "not found")
	})

	return h.recoverPanics(h.logRequests(mux))
}

func (h *handler) health(w http.ResponseWriter, r *http.Request) {
	if err := h.store.Ping(r.Context()); err != nil {
		h.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *handler) create(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}
	b, err := h.store.Create(r.Context(), in)
	if err != nil {
		h.storeError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (h *handler) list(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	bs, err := h.store.List(r.Context(), author)
	if err != nil {
		h.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, bs)
}

func (h *handler) get(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := h.store.Get(r.Context(), id)
	if err != nil {
		h.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handler) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}
	b, err := h.store.Update(r.Context(), id, in)
	if err != nil {
		h.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handler) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := h.store.Delete(r.Context(), id); err != nil {
		h.storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// storeError maps store failures onto HTTP responses.
func (h *handler) storeError(w http.ResponseWriter, err error) {
	var verr books.ValidationError
	switch {
	case errors.As(err, &verr):
		writeJSON(w, http.StatusBadRequest, errorBody{Error: "validation failed", Fields: verr})
	case errors.Is(err, books.ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found")
	default:
		h.logger.Error("store error", "err", err)
		writeError(w, http.StatusInternalServerError, "internal server error")
	}
}

// pathID parses the {id} path value, writing a 400 if it is not a positive integer.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

// decodeInput reads a single JSON object from the request body, writing the
// error response itself when that fails.
func decodeInput(w http.ResponseWriter, r *http.Request) (books.Input, bool) {
	var in books.Input
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	err := dec.Decode(&in)
	if err == nil {
		// Reject trailing content such as a second JSON document.
		if _, next := dec.Token(); next != io.EOF {
			err = errors.New("body must contain a single JSON object")
		}
	}
	if err == nil {
		return in, true
	}

	var (
		tooLarge *http.MaxBytesError
		typeErr  *json.UnmarshalTypeError
	)
	switch {
	case errors.As(err, &tooLarge):
		writeError(w, http.StatusRequestEntityTooLarge, fmt.Sprintf("request body must be at most %d bytes", tooLarge.Limit))
	case errors.As(err, &typeErr):
		writeError(w, http.StatusBadRequest, fmt.Sprintf("field %q has the wrong type: expected %s", typeErr.Field, typeErr.Type))
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "request body is required")
	default:
		writeError(w, http.StatusBadRequest, "invalid JSON body")
	}
	return books.Input{}, false
}

func methodNotAllowed(allowed ...string) http.HandlerFunc {
	allow := strings.Join(allowed, ", ")
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

type errorBody struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorBody{Error: msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// The status line is already sent, so an encode failure (client gone) has
	// nowhere useful to go.
	_ = json.NewEncoder(w).Encode(v)
}

// statusRecorder remembers the status code for the request log.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(code int) {
	s.status = code
	s.ResponseWriter.WriteHeader(code)
}

func (h *handler) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		h.logger.Info("request",
			"method", r.Method, "path", r.URL.Path,
			"status", rec.status, "duration", time.Since(start))
	})
}

func (h *handler) recoverPanics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				h.logger.Error("panic in handler", "panic", v, "path", r.URL.Path)
				writeError(w, http.StatusInternalServerError, "internal server error")
			}
		}()
		next.ServeHTTP(w, r)
	})
}
