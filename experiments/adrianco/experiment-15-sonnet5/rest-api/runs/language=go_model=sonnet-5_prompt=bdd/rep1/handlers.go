package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// API wires HTTP handlers to a Store.
type API struct {
	store *Store
}

// NewAPI creates an API backed by the given store.
func NewAPI(store *Store) *API {
	return &API{store: store}
}

// Routes returns an http.Handler with all routes registered.
func (a *API) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.handleHealth)
	mux.HandleFunc("POST /books", a.handleCreateBook)
	mux.HandleFunc("GET /books", a.handleListBooks)
	mux.HandleFunc("GET /books/{id}", a.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", a.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", a.handleDeleteBook)
	return mux
}

func (a *API) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	if errs := b.Validate(); len(errs) > 0 {
		writeError(w, http.StatusBadRequest, strings.Join(errs, "; "))
		return
	}
	created, err := a.store.Create(b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (a *API) handleListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := a.store.List(author)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) handleGetBook(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	book, err := a.store.Get(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (a *API) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	if errs := b.Validate(); len(errs) > 0 {
		writeError(w, http.StatusBadRequest, strings.Join(errs, "; "))
		return
	}
	updated, err := a.store.Update(id, b)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (a *API) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	err = a.store.Delete(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func parseID(raw string) (int64, error) {
	return strconv.ParseInt(raw, 10, 64)
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
