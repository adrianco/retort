package main

import (
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
)

// maxBodyBytes caps request bodies so a malformed client cannot exhaust memory.
const maxBodyBytes = 1 << 20 // 1 MiB

// API wires HTTP handlers to the store.
type API struct {
	store *Store
	log   *slog.Logger
}

// NewAPI builds the router for the service.
func NewAPI(store *Store, log *slog.Logger) http.Handler {
	a := &API{store: store, log: log}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)

	// jsonifyRouterErrors turns the router's own plain-text 404/405 into JSON.
	// A catch-all "/" route would do the same for 404 but would also shadow the
	// mux's method-not-allowed handling, so it is deliberately not used here.
	return a.recoverPanic(jsonifyRouterErrors(mux))
}

// routerErrorWriter replaces the plain-text body net/http writes for unmatched
// routes with our JSON error shape. Responses a handler produced itself are
// passed through untouched, identified by their JSON content type.
type routerErrorWriter struct {
	http.ResponseWriter
	replaced bool
}

func (w *routerErrorWriter) WriteHeader(status int) {
	if status == http.StatusNotFound || status == http.StatusMethodNotAllowed {
		if ct := w.Header().Get("Content-Type"); !isJSONContentType(ct) {
			w.replaced = true
			msg := "resource not found"
			if status == http.StatusMethodNotAllowed {
				msg = "method not allowed for this resource"
			}
			// The Allow header the mux set is preserved; only the body changes.
			writeError(w.ResponseWriter, status, msg, nil)
			return
		}
	}
	w.ResponseWriter.WriteHeader(status)
}

func (w *routerErrorWriter) Write(b []byte) (int, error) {
	if w.replaced {
		return len(b), nil // drop the plain-text body we already replaced
	}
	return w.ResponseWriter.Write(b)
}

// Unwrap lets http.ResponseController reach the underlying writer.
func (w *routerErrorWriter) Unwrap() http.ResponseWriter { return w.ResponseWriter }

func jsonifyRouterErrors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		next.ServeHTTP(&routerErrorWriter{ResponseWriter: w}, r)
	})
}

// errorBody is the JSON shape returned for every non-2xx response.
type errorBody struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func (a *API) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(r.Context()); err != nil {
		a.log.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status":   "unavailable",
			"database": "down",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status":   "ok",
		"database": "up",
	})
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}

	book, err := a.store.Create(r.Context(), in)
	if errors.Is(err, ErrDuplicateISBN) {
		writeError(w, http.StatusConflict, err.Error(), nil)
		return
	}
	if err != nil {
		a.internalError(w, "create book", err)
		return
	}

	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		a.internalError(w, "list books", err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"books": books,
		"count": len(books),
	})
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}

	book, err := a.store.Get(r.Context(), id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, err.Error(), nil)
		return
	}
	if err != nil {
		a.internalError(w, "get book", err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeInput(w, r)
	if !ok {
		return
	}

	book, err := a.store.Update(r.Context(), id, in)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, err.Error(), nil)
	case errors.Is(err, ErrDuplicateISBN):
		writeError(w, http.StatusConflict, err.Error(), nil)
	case err != nil:
		a.internalError(w, "update book", err)
	default:
		writeJSON(w, http.StatusOK, book)
	}
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}

	err := a.store.Delete(r.Context(), id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, err.Error(), nil)
		return
	}
	if err != nil {
		a.internalError(w, "delete book", err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// parseID reads the {id} path segment, writing a 400 if it is not a positive integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer", nil)
		return 0, false
	}
	return id, true
}

// decodeInput parses and validates a request body, writing the appropriate
// error response itself when the body is unusable.
func decodeInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	if ct := r.Header.Get("Content-Type"); ct != "" && !isJSONContentType(ct) {
		writeError(w, http.StatusUnsupportedMediaType, "content-type must be application/json", nil)
		return BookInput{}, false
	}

	var in BookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()

	if err := dec.Decode(&in); err != nil {
		var maxErr *http.MaxBytesError
		if errors.As(err, &maxErr) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body is too large", nil)
			return BookInput{}, false
		}
		msg := "request body must be valid JSON"
		if errors.Is(err, io.EOF) {
			msg = "request body is required"
		}
		writeError(w, http.StatusBadRequest, msg, nil)
		return BookInput{}, false
	}
	// Reject trailing content so `{"title":"a"} {"title":"b"}` is not silently accepted.
	if err := dec.Decode(new(struct{})); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object", nil)
		return BookInput{}, false
	}

	in.Normalize()
	if problems := in.Validate(); len(problems) > 0 {
		writeError(w, http.StatusUnprocessableEntity, "validation failed", problems)
		return BookInput{}, false
	}
	return in, true
}

func isJSONContentType(ct string) bool {
	mediaType, _, _ := strings.Cut(ct, ";")
	return strings.EqualFold(strings.TrimSpace(mediaType), "application/json")
}

func (a *API) internalError(w http.ResponseWriter, op string, err error) {
	a.log.Error(op+" failed", "err", err)
	writeError(w, http.StatusInternalServerError, "internal server error", nil)
}

// recoverPanic keeps a handler bug from killing the process or hanging the client.
func (a *API) recoverPanic(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				a.log.Error("panic serving request", "method", r.Method, "path", r.URL.Path, "panic", rec)
				writeError(w, http.StatusInternalServerError, "internal server error", nil)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func writeError(w http.ResponseWriter, status int, msg string, fields map[string]string) {
	writeJSON(w, status, errorBody{Error: msg, Fields: fields})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	body, err := json.Marshal(payload)
	if err != nil {
		// Marshalling our own types should never fail; fall back to a bare 500.
		http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	w.Write(body)
}
