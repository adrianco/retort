package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// NewHandler returns the HTTP router for the API.
func NewHandler(s *Store) http.Handler {
	h := &api{store: s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("POST /books", h.create)
	mux.HandleFunc("GET /books", h.list)
	mux.HandleFunc("GET /books/{id}", h.get)
	mux.HandleFunc("PUT /books/{id}", h.update)
	mux.HandleFunc("DELETE /books/{id}", h.delete)
	return mux
}

type api struct{ store *Store }

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func (a *api) fail(w http.ResponseWriter, err error) {
	if errors.Is(err, errNotFound) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	}
	log.Printf("internal error: %v", err)
	writeErr(w, http.StatusInternalServerError, "internal server error")
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeErr(w, http.StatusBadRequest, "invalid id")
		return 0, false
	}
	return id, true
}

// decode reads and validates a book from the request body.
func decode(w http.ResponseWriter, r *http.Request) (*Book, bool) {
	var b Book
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON body")
		return nil, false
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	switch {
	case b.Title == "":
		writeErr(w, http.StatusBadRequest, "title is required")
	case b.Author == "":
		writeErr(w, http.StatusBadRequest, "author is required")
	case b.Year < 0:
		writeErr(w, http.StatusBadRequest, "year must not be negative")
	default:
		return &b, true
	}
	return nil, false
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) create(w http.ResponseWriter, r *http.Request) {
	b, ok := decode(w, r)
	if !ok {
		return
	}
	b.ID = 0
	if err := a.store.Create(b); err != nil {
		a.fail(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (a *api) list(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.URL.Query().Get("author"))
	if err != nil {
		a.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *api) get(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := a.store.Get(id)
	if err != nil {
		a.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) update(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, ok := decode(w, r)
	if !ok {
		return
	}
	b.ID = id
	if err := a.store.Update(b); err != nil {
		a.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(id); err != nil {
		a.fail(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
