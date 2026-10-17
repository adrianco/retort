package main

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
)

// maxBodyBytes caps request bodies. A book record is far smaller than this.
const maxBodyBytes = 1 << 20

// api holds the dependencies shared by the HTTP handlers.
type api struct {
	store  *Store
	logger *slog.Logger
}

// health reports 200 when the database responds, and 503 otherwise.
func (a *api) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := a.store.Ping(ctx); err != nil {
		a.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// listBooks returns all books, optionally filtered by ?author=.
func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := a.store.List(r.Context(), author)
	if err != nil {
		a.serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

// getBook returns a single book by ID.
func (a *api) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	book, err := a.store.Get(r.Context(), id)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, ErrNotFound.Error())
	case err != nil:
		a.serverError(w, err)
	default:
		writeJSON(w, http.StatusOK, book)
	}
}

// createBook adds a book and responds 201 with a Location header.
func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	book, ok := readBook(w, r)
	if !ok {
		return
	}
	created, err := a.store.Create(r.Context(), book)
	if err != nil {
		a.serverError(w, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", created.ID))
	writeJSON(w, http.StatusCreated, created)
}

// updateBook replaces the book with the given ID. The body must contain the full record.
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
		writeError(w, http.StatusNotFound, ErrNotFound.Error())
	case err != nil:
		a.serverError(w, err)
	default:
		writeJSON(w, http.StatusOK, updated)
	}
}

// deleteBook removes a book and responds 204 No Content.
func (a *api) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	err := a.store.Delete(r.Context(), id)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, ErrNotFound.Error())
	case err != nil:
		a.serverError(w, err)
	default:
		w.WriteHeader(http.StatusNoContent)
	}
}

// serverError logs err and responds 500 without exposing internal details.
func (a *api) serverError(w http.ResponseWriter, err error) {
	a.logger.Error("request failed", "err", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// pathID parses the {id} path segment. It writes a 400 response and returns
// false if the segment is not a positive integer.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

// readBook decodes and validates the request body as a book. On failure it
// writes the error response and returns false.
func readBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var in BookInput
	if !decodeBody(w, r, &in) {
		return Book{}, false
	}
	book, errs := validateBook(in, time.Now())
	if errs != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":  "validation failed",
			"fields": errs,
		})
		return Book{}, false
	}
	return book, true
}

// decodeBody parses exactly one JSON object from the request body into dst,
// rejecting unknown fields. On failure it writes the error response and returns false.
func decodeBody(w http.ResponseWriter, r *http.Request, dst any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()

	if err := dec.Decode(dst); err != nil {
		var tooLarge *http.MaxBytesError
		switch {
		case errors.As(err, &tooLarge):
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		case errors.Is(err, io.EOF):
			writeError(w, http.StatusBadRequest, "request body is required")
		default:
			writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		}
		return false
	}
	// Reject trailing content such as a second JSON value.
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return false
	}
	return true
}
