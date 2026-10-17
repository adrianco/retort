package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"maps"
	"net/http"
	"reflect"
	"slices"
	"strconv"
	"strings"
	"time"
)

// maxBodyBytes caps request bodies. A book record is a few hundred bytes.
const maxBodyBytes = 1 << 20

// NewHandler returns the HTTP API, backed by store.
func NewHandler(store *Store, logger *slog.Logger) http.Handler {
	a := &api{store: store, logger: logger}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", route(map[string]http.HandlerFunc{
		http.MethodGet: a.health,
	}))
	mux.HandleFunc("/books", route(map[string]http.HandlerFunc{
		http.MethodGet:  a.listBooks,
		http.MethodPost: a.createBook,
	}))
	mux.HandleFunc("/books/{id}", route(map[string]http.HandlerFunc{
		http.MethodGet:    a.getBook,
		http.MethodPut:    a.updateBook,
		http.MethodDelete: a.deleteBook,
	}))
	// Without this catch-all, ServeMux answers unknown paths in plain text.
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "not found")
	})

	return a.logRequests(mux)
}

type api struct {
	store  *Store
	logger *slog.Logger
}

// route dispatches a request to the handler for its method. A method with no
// handler gets a 405 that lists the allowed methods. HEAD is served by the GET
// handler, as it is for net/http's own method patterns.
func route(handlers map[string]http.HandlerFunc) http.HandlerFunc {
	if get, ok := handlers[http.MethodGet]; ok {
		handlers[http.MethodHead] = get
	}
	allow := strings.Join(slices.Sorted(maps.Keys(handlers)), ", ")

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

// health reports 200 while the database answers, and 503 otherwise.
func (a *api) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := a.store.Ping(ctx); err != nil {
		a.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// listBooks handles GET /books, optionally filtered by ?author=.
func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := a.store.List(r.Context(), author)
	if err != nil {
		a.serverError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

// createBook handles POST /books.
func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	book, ok := readBook(w, r)
	if !ok {
		return
	}
	created, err := a.store.Create(r.Context(), book)
	if err != nil {
		a.serverError(w, r, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
}

// getBook handles GET /books/{id}.
func (a *api) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	book, err := a.store.Get(r.Context(), id)
	switch {
	case errors.Is(err, ErrNotFound):
		writeNotFound(w, id)
	case err != nil:
		a.serverError(w, r, err)
	default:
		writeJSON(w, http.StatusOK, book)
	}
}

// updateBook handles PUT /books/{id}. The body replaces the whole record, so
// an omitted year or ISBN is cleared.
func (a *api) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	book, ok := readBook(w, r)
	if !ok {
		return
	}
	updated, err := a.store.Update(r.Context(), id, book)
	switch {
	case errors.Is(err, ErrNotFound):
		writeNotFound(w, id)
	case err != nil:
		a.serverError(w, r, err)
	default:
		writeJSON(w, http.StatusOK, updated)
	}
}

// deleteBook handles DELETE /books/{id}.
func (a *api) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	err := a.store.Delete(r.Context(), id)
	switch {
	case errors.Is(err, ErrNotFound):
		writeNotFound(w, id)
	case err != nil:
		a.serverError(w, r, err)
	default:
		w.WriteHeader(http.StatusNoContent)
	}
}

// serverError logs err and sends a generic 500, keeping internal detail out of
// the response.
func (a *api) serverError(w http.ResponseWriter, r *http.Request, err error) {
	a.logger.Error("request failed", "method", r.Method, "path", r.URL.Path, "error", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// logRequests logs the method, path, status and duration of each request.
func (a *api) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		a.logger.Info("request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rec.status,
			"duration", time.Since(start),
		)
	})
}

// statusRecorder remembers the status code that the wrapped handler wrote.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(code int) {
	s.status = code
	s.ResponseWriter.WriteHeader(code)
}

// pathID parses the {id} segment. Anything other than a positive integer is a
// malformed request, not a missing book, so it gets a 400.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

// readBook decodes and validates the JSON body of a POST or PUT. If the body is
// unacceptable it writes the error response and returns false.
func readBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields() // a misspelt field should fail, not be silently dropped

	var in bookInput
	if err := dec.Decode(&in); err != nil {
		writeDecodeError(w, err)
		return Book{}, false
	}
	// Anything after the object, even a second object, makes the body invalid.
	if err := dec.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return Book{}, false
	}

	book, errs := in.toBook(time.Now())
	if len(errs) > 0 {
		writeFieldErrors(w, errs)
		return Book{}, false
	}
	return book, true
}

// writeDecodeError reports a request body that could not be decoded into a
// bookInput.
func writeDecodeError(w http.ResponseWriter, err error) {
	var tooLarge *http.MaxBytesError
	var typeErr *json.UnmarshalTypeError

	switch {
	case errors.As(err, &tooLarge):
		writeError(w, http.StatusRequestEntityTooLarge, fmt.Sprintf("request body exceeds %d bytes", maxBodyBytes))
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "request body is empty")
	case errors.As(err, &typeErr) && typeErr.Field == "":
		writeError(w, http.StatusBadRequest, "request body must be a JSON object")
	case errors.As(err, &typeErr):
		writeFieldErrors(w, fieldErrors{typeErr.Field: "must be " + jsonTypeName(typeErr.Type)})
	default:
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
	}
}

// jsonTypeName names the JSON type that a Go field of type t expects.
func jsonTypeName(t reflect.Type) string {
	switch t.Kind() {
	case reflect.String:
		return "a string"
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return "an integer"
	}
	return "a " + t.Kind().String()
}

func writeNotFound(w http.ResponseWriter, id int64) {
	writeError(w, http.StatusNotFound, fmt.Sprintf("book %d not found", id))
}

// errorBody is the JSON shape of every error response. Fields is set only for
// validation failures, and names each offending input field.
type errorBody struct {
	Error  string      `json:"error"`
	Fields fieldErrors `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorBody{Error: msg})
}

func writeFieldErrors(w http.ResponseWriter, fields fieldErrors) {
	writeJSON(w, http.StatusBadRequest, errorBody{Error: "validation failed", Fields: fields})
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// An encoding error here can only come from a failed write to the client,
	// and there is nothing useful to do about that.
	_ = json.NewEncoder(w).Encode(body)
}
