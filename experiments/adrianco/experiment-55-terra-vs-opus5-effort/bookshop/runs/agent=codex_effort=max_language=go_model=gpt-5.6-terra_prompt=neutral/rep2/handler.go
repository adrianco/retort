package main

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"
)

const maxRequestBodyBytes = 1 << 20 // 1 MiB

// API serves the book collection REST endpoints.
type API struct {
	store *Store
}

// NewHandler returns an HTTP handler for the book API.
func NewHandler(store *Store) http.Handler {
	return &API{store: store}
}

func (api *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch {
	case r.URL.Path == "/health":
		if r.Method != http.MethodGet {
			methodNotAllowed(w, http.MethodGet)
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	case r.URL.Path == "/books":
		api.handleBooks(w, r)
	case strings.HasPrefix(r.URL.Path, "/books/"):
		api.handleBook(w, r)
	default:
		writeError(w, http.StatusNotFound, "endpoint not found")
	}
}

func (api *API) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		input, ok := decodeAndValidateBookInput(w, r)
		if !ok {
			return
		}

		book, err := api.store.Create(r.Context(), input)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
		writeJSON(w, http.StatusCreated, book)
	case http.MethodGet:
		books, err := api.store.List(r.Context(), r.URL.Query().Get("author"))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		writeJSON(w, http.StatusOK, books)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPost)
	}
}

func (api *API) handleBook(w http.ResponseWriter, r *http.Request) {
	idPart := strings.TrimPrefix(r.URL.Path, "/books/")
	if idPart == "" || strings.Contains(idPart, "/") {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	id, err := strconv.ParseInt(idPart, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	switch r.Method {
	case http.MethodGet:
		book, err := api.store.Get(r.Context(), id)
		if handleStoreError(w, err, "could not get book") {
			return
		}
		writeJSON(w, http.StatusOK, book)
	case http.MethodPut:
		input, ok := decodeAndValidateBookInput(w, r)
		if !ok {
			return
		}
		book, err := api.store.Update(r.Context(), id, input)
		if handleStoreError(w, err, "could not update book") {
			return
		}
		writeJSON(w, http.StatusOK, book)
	case http.MethodDelete:
		err := api.store.Delete(r.Context(), id)
		if handleStoreError(w, err, "could not delete book") {
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPut, http.MethodDelete)
	}
}

func decodeAndValidateBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	r.Body = http.MaxBytesReader(w, r.Body, maxRequestBodyBytes)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()

	var input BookInput
	if err := decoder.Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "request body must be a valid JSON book")
		return BookInput{}, false
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain one JSON object")
		return BookInput{}, false
	}

	input.Title = strings.TrimSpace(input.Title)
	input.Author = strings.TrimSpace(input.Author)
	input.ISBN = strings.TrimSpace(input.ISBN)
	if input.Title == "" && input.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return BookInput{}, false
	}
	if input.Title == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return BookInput{}, false
	}
	if input.Author == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return BookInput{}, false
	}

	return input, true
}

// handleStoreError writes a response for the error and reports whether an
// error was handled.
func handleStoreError(w http.ResponseWriter, err error, internalMessage string) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return true
	}
	writeError(w, http.StatusInternalServerError, internalMessage)
	return true
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
	_ = json.NewEncoder(w).Encode(value)
}
