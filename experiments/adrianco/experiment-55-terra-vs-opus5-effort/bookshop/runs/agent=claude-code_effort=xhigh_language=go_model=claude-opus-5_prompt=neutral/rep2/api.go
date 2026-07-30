package main

import (
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

// maxBodyBytes caps request bodies. A book record is a few hundred bytes, so
// this is generous while still bounding what a single request can allocate.
const maxBodyBytes = 1 << 20

// API wires the HTTP endpoints to the store.
type API struct {
	store *Store
	log   *slog.Logger
	// now supplies the clock used for validation (the current year bound);
	// it is injectable for tests.
	now func() time.Time
}

// NewAPI returns an API backed by store. A nil logger discards log output.
func NewAPI(store *Store, log *slog.Logger) *API {
	if log == nil {
		log = slog.New(slog.DiscardHandler)
	}
	return &API{store: store, log: log, now: time.Now}
}

// Routes returns the fully wired handler, including logging and panic
// recovery.
//
// Each path is registered twice: once per supported method, and once without
// a method. Go's ServeMux prefers the more specific method-qualified pattern,
// so the bare registration is reached only by an unsupported method, which
// lets it answer 405 with a JSON body and an Allow header instead of the
// mux's built-in plain-text response.
func (a *API) Routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", a.health)
	mux.Handle("/health", methodNotAllowed(http.MethodGet))

	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.Handle("/books", methodNotAllowed(http.MethodGet, http.MethodPost))

	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
	mux.Handle("/books/{id}", methodNotAllowed(http.MethodGet, http.MethodPut, http.MethodDelete))

	mux.HandleFunc("/", a.notFound)

	// Recovery sits inside the access log so a panicking request is still
	// logged, with the 500 the client actually saw.
	return a.logRequests(a.recoverPanic(mux))
}

// GET /health reports service and database status.
func (a *API) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(r.Context()); err != nil {
		a.log.ErrorContext(r.Context(), "health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status":   "unavailable",
			"database": "unavailable",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status":   "ok",
		"database": "ok",
	})
}

// POST /books creates a book.
func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := a.decodeBook(w, r)
	if !ok {
		return
	}

	book, fieldErrs := in.Validate(a.now())
	if len(fieldErrs) > 0 {
		writeValidationError(w, fieldErrs)
		return
	}

	created, err := a.store.Create(r.Context(), book)
	switch {
	case errors.Is(err, ErrISBNTaken):
		writeError(w, http.StatusConflict, "isbn_taken", "another book already has this ISBN")
		return
	case err != nil:
		a.internalError(w, r, "create book", err)
		return
	}

	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
}

// GET /books lists books, optionally filtered by author. Unrecognised query
// parameters are ignored, as HTTP convention expects.
func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.Context(), ListFilter{
		Author: strings.TrimSpace(r.URL.Query().Get("author")),
	})
	if err != nil {
		a.internalError(w, r, "list books", err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

// GET /books/{id} returns one book.
func (a *API) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}

	book, err := a.store.Get(r.Context(), id)
	switch {
	case errors.Is(err, ErrNotFound):
		writeBookNotFound(w, id)
		return
	case err != nil:
		a.internalError(w, r, "get book", err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// PUT /books/{id} replaces a book. As a full replacement, title and author
// are required and any omitted optional field is cleared.
func (a *API) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := a.decodeBook(w, r)
	if !ok {
		return
	}

	book, fieldErrs := in.Validate(a.now())
	if len(fieldErrs) > 0 {
		writeValidationError(w, fieldErrs)
		return
	}

	updated, err := a.store.Update(r.Context(), id, book)
	switch {
	case errors.Is(err, ErrNotFound):
		writeBookNotFound(w, id)
		return
	case errors.Is(err, ErrISBNTaken):
		writeError(w, http.StatusConflict, "isbn_taken", "another book already has this ISBN")
		return
	case err != nil:
		a.internalError(w, r, "update book", err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

// DELETE /books/{id} removes a book.
func (a *API) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}

	err := a.store.Delete(r.Context(), id)
	switch {
	case errors.Is(err, ErrNotFound):
		writeBookNotFound(w, id)
		return
	case err != nil:
		a.internalError(w, r, "delete book", err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (a *API) notFound(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusNotFound, "not_found",
		fmt.Sprintf("no route for %s %s", r.Method, r.URL.Path))
}

// decodeBook reads and strictly decodes a request body, writing the
// appropriate 4xx response and reporting false if it cannot.
func (a *API) decodeBook(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput

	// An explicit Content-Type of something other than JSON is a client bug
	// worth naming; a missing one is tolerated.
	if ct := r.Header.Get("Content-Type"); ct != "" {
		mediaType, _, err := mime.ParseMediaType(ct)
		if err != nil || mediaType != "application/json" {
			writeError(w, http.StatusUnsupportedMediaType, "unsupported_media_type",
				"Content-Type must be application/json")
			return in, false
		}
	}

	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	// Reject misspelled fields rather than silently ignoring them: a typo in
	// "title" would otherwise look like a successful write that lost data.
	dec.DisallowUnknownFields()

	switch err := dec.Decode(&in); {
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "invalid_json", "request body is empty")
		return in, false
	case err != nil:
		var maxBytesErr *http.MaxBytesError
		if errors.As(err, &maxBytesErr) {
			writeError(w, http.StatusRequestEntityTooLarge, "request_too_large",
				fmt.Sprintf("request body must be at most %d bytes", maxBodyBytes))
			return in, false
		}
		writeError(w, http.StatusBadRequest, "invalid_json", decodeErrorMessage(err))
		return in, false
	}

	// A body of "{...} {...}" is ambiguous; accept exactly one JSON value.
	if dec.More() {
		writeError(w, http.StatusBadRequest, "invalid_json",
			"request body must contain a single JSON object")
		return in, false
	}
	return in, true
}

// decodeErrorMessage turns a json decode failure into something a client can
// act on without leaking internals.
func decodeErrorMessage(err error) string {
	var (
		typeErr   *json.UnmarshalTypeError
		syntaxErr *json.SyntaxError
	)
	switch {
	case errors.As(err, &typeErr):
		if typeErr.Field != "" {
			return fmt.Sprintf("field %q must be of type %s", typeErr.Field, typeErr.Type)
		}
		return fmt.Sprintf("body must be a JSON object, got %s", typeErr.Value)
	case errors.As(err, &syntaxErr):
		return fmt.Sprintf("malformed JSON at byte offset %d", syntaxErr.Offset)
	default:
		// Covers DisallowUnknownFields, whose error carries no dedicated
		// type but whose message ("json: unknown field ...") is useful.
		return strings.TrimPrefix(err.Error(), "json: ")
	}
}

// parseID extracts the {id} path value.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid_id",
			fmt.Sprintf("book id must be a positive integer, got %q", raw))
		return 0, false
	}
	return id, true
}

// ErrorBody is the response envelope for every error this API returns.
type ErrorBody struct {
	Error ErrorDetail `json:"error"`
}

// ErrorDetail carries a stable machine-readable code alongside the human
// message, plus per-field detail for validation failures.
type ErrorDetail struct {
	Code    string       `json:"code"`
	Message string       `json:"message"`
	Fields  []FieldError `json:"fields,omitempty"`
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	// Encode first: a marshalling failure after WriteHeader would leave a
	// successful status on a truncated body.
	payload, err := json.Marshal(body)
	if err != nil {
		payload, status = []byte(`{"error":{"code":"internal_error","message":"failed to encode response"}}`),
			http.StatusInternalServerError
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	w.Write(append(payload, '\n'))
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, ErrorBody{ErrorDetail{Code: code, Message: message}})
}

func writeValidationError(w http.ResponseWriter, fields []FieldError) {
	writeJSON(w, http.StatusBadRequest, ErrorBody{ErrorDetail{
		Code:    "validation_failed",
		Message: "the request body failed validation",
		Fields:  fields,
	}})
}

func writeBookNotFound(w http.ResponseWriter, id int64) {
	writeError(w, http.StatusNotFound, "not_found", fmt.Sprintf("no book with id %d", id))
}

// internalError logs the cause and returns an opaque 500: the details belong
// in the log, not in the response.
func (a *API) internalError(w http.ResponseWriter, r *http.Request, op string, err error) {
	a.log.ErrorContext(r.Context(), "request failed", "op", op, "error", err,
		"method", r.Method, "path", r.URL.Path)
	writeError(w, http.StatusInternalServerError, "internal_error", "internal server error")
}

func methodNotAllowed(allowed ...string) http.Handler {
	allow := strings.Join(allowed, ", ")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed",
			fmt.Sprintf("%s is not allowed on %s; allowed: %s", r.Method, r.URL.Path, allow))
	})
}

// statusRecorder captures the status code for the access log.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (rec *statusRecorder) WriteHeader(status int) {
	rec.status = status
	rec.ResponseWriter.WriteHeader(status)
}

func (a *API) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		// Default to 200: a handler that writes a body without calling
		// WriteHeader has implicitly sent one.
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		a.log.InfoContext(r.Context(), "request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rec.status,
			"duration", time.Since(start).String())
	})
}

func (a *API) recoverPanic(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				a.log.ErrorContext(r.Context(), "panic serving request",
					"panic", fmt.Sprint(v), "method", r.Method, "path", r.URL.Path)
				// Close the connection: the response may be partly
				// written and is no longer trustworthy.
				w.Header().Set("Connection", "close")
				writeError(w, http.StatusInternalServerError, "internal_error", "internal server error")
			}
		}()
		next.ServeHTTP(w, r)
	})
}
