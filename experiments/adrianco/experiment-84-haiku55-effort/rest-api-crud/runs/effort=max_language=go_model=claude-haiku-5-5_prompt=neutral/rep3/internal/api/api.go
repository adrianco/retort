// Package api serves the book collection over HTTP. Requests and responses use
// JSON. Errors are returned as {"error": "..."} with a matching status code.
package api

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"bookapi/internal/book"
	"bookapi/internal/store"
)

// maxBodyBytes caps the size of a request body.
const maxBodyBytes = 1 << 20

const malformedBody = "malformed JSON: expected an object with string fields title, author and isbn, and an integer year"

// NewRouter returns the HTTP handler for the book API.
func NewRouter(st *store.Store, logger *slog.Logger) http.Handler {
	h := &handler{store: st, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", byMethod(map[string]http.HandlerFunc{
		http.MethodGet: h.health,
	}))
	mux.HandleFunc("/books", byMethod(map[string]http.HandlerFunc{
		http.MethodGet:  h.listBooks,
		http.MethodPost: h.createBook,
	}))
	mux.HandleFunc("/books/{id}", byMethod(map[string]http.HandlerFunc{
		http.MethodGet:    h.getBook,
		http.MethodPut:    h.updateBook,
		http.MethodDelete: h.deleteBook,
	}))
	// Without this catch-all, unknown paths get the mux's plain-text 404.
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "no such endpoint")
	})

	return logRequests(logger, recoverPanics(logger, mux))
}

// byMethod dispatches on the request method. Any other method gets a 405 that
// lists the allowed methods in the Allow header. HEAD is served by the GET
// handler, and net/http drops the body of a HEAD response.
func byMethod(handlers map[string]http.HandlerFunc) http.HandlerFunc {
	if get, ok := handlers[http.MethodGet]; ok {
		handlers[http.MethodHead] = get
	}
	methods := make([]string, 0, len(handlers))
	for m := range handlers {
		methods = append(methods, m)
	}
	sort.Strings(methods)
	allow := strings.Join(methods, ", ")

	return func(w http.ResponseWriter, r *http.Request) {
		h, ok := handlers[r.Method]
		if !ok {
			w.Header().Set("Allow", allow)
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		h(w, r)
	}
}

type handler struct {
	store  *store.Store
	logger *slog.Logger
}

func (h *handler) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := h.store.Ping(ctx); err != nil {
		h.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *handler) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := h.store.List(r.Context(), author)
	if err != nil {
		h.serverError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (h *handler) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	created, err := h.store.Create(r.Context(), in)
	if err != nil {
		h.serverError(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
}

func (h *handler) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := h.store.Get(r.Context(), id)
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found")
	case err != nil:
		h.serverError(w, r, err)
	default:
		writeJSON(w, http.StatusOK, b)
	}
}

// updateBook replaces the whole book. Omitted optional fields are cleared.
func (h *handler) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	updated, err := h.store.Update(r.Context(), id, in)
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found")
	case err != nil:
		h.serverError(w, r, err)
	default:
		writeJSON(w, http.StatusOK, updated)
	}
}

func (h *handler) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	err := h.store.Delete(r.Context(), id)
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found")
	case err != nil:
		h.serverError(w, r, err)
	default:
		w.WriteHeader(http.StatusNoContent)
	}
}

// serverError logs err and sends a generic 500, keeping internal details out of
// the response.
func (h *handler) serverError(w http.ResponseWriter, r *http.Request, err error) {
	h.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "err", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// pathID parses the {id} path segment. On failure it writes a 400 and returns false.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

// decodeBook reads one JSON object from the request body and validates it. On
// failure it writes the error response and returns false.
func decodeBook(w http.ResponseWriter, r *http.Request) (book.Input, bool) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)

	var in book.Input
	var tooLarge *http.MaxBytesError
	switch err := dec.Decode(&in); {
	case errors.As(err, &tooLarge):
		writeError(w, http.StatusRequestEntityTooLarge, "request body exceeds 1 MiB")
		return book.Input{}, false
	case err != nil:
		writeError(w, http.StatusBadRequest, malformedBody)
		return book.Input{}, false
	}
	// Reject anything after the object, such as a second JSON document.
	if err := dec.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, malformedBody)
		return book.Input{}, false
	}

	clean, verr := in.Validate()
	if verr != nil {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "validation failed", Details: verr.Fields})
		return book.Input{}, false
	}
	return clean, true
}

type errorResponse struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// The status is already sent, so an encoding error can only mean the client
	// has gone away. There is nothing useful left to do with it.
	_ = json.NewEncoder(w).Encode(body)
}
