package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
)

const maxRequestBodyBytes = 1 << 20 // 1 MiB

// API is the HTTP handler for the book collection service.
type API struct {
	store *Store
}

// NewAPI creates an HTTP handler backed by store.
func NewAPI(store *Store) *API {
	return &API{store: store}
}

// ServeHTTP routes requests without requiring an external web framework.
func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch r.URL.Path {
	case "/health":
		a.handleHealth(w, r)
		return
	case "/books":
		a.handleBooks(w, r)
		return
	}

	if strings.HasPrefix(r.URL.Path, "/books/") {
		a.handleBook(w, r)
		return
	}

	writeError(w, http.StatusNotFound, "route not found")
}

func (a *API) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w, http.MethodGet)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		a.createBook(w, r)
	case http.MethodGet:
		a.listBooks(w, r)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPost)
	}
}

func (a *API) handleBook(w http.ResponseWriter, r *http.Request) {
	pathID := strings.TrimPrefix(r.URL.Path, "/books/")
	if pathID == "" || strings.Contains(pathID, "/") {
		writeError(w, http.StatusNotFound, "route not found")
		return
	}

	id, err := strconv.ParseInt(pathID, 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "book ID must be a positive integer")
		return
	}

	switch r.Method {
	case http.MethodGet:
		a.getBook(w, r, id)
	case http.MethodPut:
		a.updateBook(w, r, id)
	case http.MethodDelete:
		a.deleteBook(w, r, id)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPut, http.MethodDelete)
	}
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	input, ok := decodeAndValidateBook(w, r)
	if !ok {
		return
	}

	book, err := a.store.Create(r.Context(), input)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not create book")
		return
	}
	writeJSON(w, http.StatusCreated, book)
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request, id int64) {
	book, err := a.store.Get(r.Context(), id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request, id int64) {
	input, ok := decodeAndValidateBook(w, r)
	if !ok {
		return
	}

	book, err := a.store.Update(r.Context(), id, input)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not update book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request, id int64) {
	if err := a.store.Delete(r.Context(), id); err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		writeError(w, http.StatusInternalServerError, "could not delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func decodeAndValidateBook(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	defer r.Body.Close()

	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxRequestBodyBytes))
	decoder.DisallowUnknownFields()
	var input BookInput
	if err := decoder.Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "request body must be a valid JSON book")
		return BookInput{}, false
	}
	if err := ensureOnlyOneJSONValue(decoder); err != nil {
		writeError(w, http.StatusBadRequest, "request body must contain one JSON object")
		return BookInput{}, false
	}

	input.Title = strings.TrimSpace(input.Title)
	input.Author = strings.TrimSpace(input.Author)
	input.ISBN = strings.TrimSpace(input.ISBN)
	if input.Title == "" || input.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return BookInput{}, false
	}
	if input.Year < 0 {
		writeError(w, http.StatusBadRequest, "year cannot be negative")
		return BookInput{}, false
	}
	return input, true
}

func ensureOnlyOneJSONValue(decoder *json.Decoder) error {
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		if err == nil {
			return fmt.Errorf("multiple JSON values")
		}
		return err
	}
	return nil
}

func methodNotAllowed(w http.ResponseWriter, methods ...string) {
	w.Header().Set("Allow", strings.Join(methods, ", "))
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(value); err != nil {
		// The only values written by this service are JSON-encodable. There is no
		// useful response recovery once headers and a status have been sent.
		return
	}
}
