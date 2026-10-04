package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
)

// maxBodyBytes caps the size of a request body.
const maxBodyBytes = 1 << 20

// API serves the book collection over HTTP.
type API struct {
	store *Store
}

// NewHandler returns the HTTP handler exposing the book API backed by store.
func NewHandler(store *Store) http.Handler {
	api := &API{store: store}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", api.health)
	mux.HandleFunc("/books", api.books)
	mux.HandleFunc("/books/{id}", api.book)
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "resource not found")
	})
	return mux
}

func (a *API) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		methodNotAllowed(w, "GET, HEAD")
		return
	}
	if err := a.store.Ping(r.Context()); err != nil {
		log.Printf("health check: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// books handles the collection resource, /books.
func (a *API) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet, http.MethodHead:
		a.listBooks(w, r)
	case http.MethodPost:
		a.createBook(w, r)
	default:
		methodNotAllowed(w, "GET, HEAD, POST")
	}
}

// book handles a single item resource, /books/{id}.
func (a *API) book(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return
	}

	switch r.Method {
	case http.MethodGet, http.MethodHead:
		a.getBook(w, r, id)
	case http.MethodPut:
		a.updateBook(w, r, id)
	case http.MethodDelete:
		a.deleteBook(w, r, id)
	default:
		methodNotAllowed(w, "GET, HEAD, PUT, DELETE")
	}
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := readBookInput(w, r)
	if !ok {
		return
	}
	book, err := a.store.Create(r.Context(), in)
	if err != nil {
		internalError(w, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	book, err := a.store.Get(r.Context(), id)
	if err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	in, ok := readBookInput(w, r)
	if !ok {
		return
	}
	book, err := a.store.Update(r.Context(), id, in)
	if err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	if err := a.store.Delete(r.Context(), id); err != nil {
		storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// readBookInput decodes and validates a book payload. On failure it writes the
// error response itself and returns false.
func readBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		writeDecodeError(w, err)
		return BookInput{}, false
	}
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return BookInput{}, false
	}

	in.Normalize()
	if problems := in.Validate(); len(problems) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":  "validation failed",
			"fields": problems,
		})
		return BookInput{}, false
	}
	return in, true
}

func writeDecodeError(w http.ResponseWriter, err error) {
	var tooLarge *http.MaxBytesError
	var typeErr *json.UnmarshalTypeError
	switch {
	case errors.As(err, &tooLarge):
		writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
	case errors.As(err, &typeErr) && typeErr.Field != "":
		writeError(w, http.StatusBadRequest,
			fmt.Sprintf("field %q has the wrong type: expected %s", typeErr.Field, typeErr.Type))
	case errors.Is(err, io.EOF):
		writeError(w, http.StatusBadRequest, "request body must not be empty")
	default:
		writeError(w, http.StatusBadRequest, "request body must be a valid JSON object")
	}
}

// storeError maps a store failure to a 404 or 500 response.
func storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	internalError(w, err)
}

func internalError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func methodNotAllowed(w http.ResponseWriter, allow string) {
	w.Header().Set("Allow", allow)
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}
