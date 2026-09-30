package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// NewHandler builds the HTTP router for the API.
func NewHandler(s *Store) http.Handler {
	a := &api{store: s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.create)
	mux.HandleFunc("GET /books", a.list)
	mux.HandleFunc("GET /books/{id}", a.get)
	mux.HandleFunc("PUT /books/{id}", a.update)
	mux.HandleFunc("DELETE /books/{id}", a.delete)
	return mux
}

type api struct{ store *Store }

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func serverError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// decodeBook parses and validates a request body.
func decodeBook(r *http.Request) (*Book, string) {
	r.Body = http.MaxBytesReader(nil, r.Body, 1<<20)
	var b Book
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(&b); err != nil {
		return nil, "invalid JSON body"
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	switch {
	case b.Title == "":
		return nil, "title is required"
	case b.Author == "":
		return nil, "author is required"
	case b.Year < 0 || b.Year > time.Now().Year()+1:
		return nil, "year is out of range"
	}
	return &b, ""
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func (a *api) create(w http.ResponseWriter, r *http.Request) {
	b, msg := decodeBook(r)
	if msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}
	b.ID = 0
	if err := a.store.Create(b); err != nil {
		serverError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (a *api) list(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.URL.Query().Get("author"))
	if err != nil {
		serverError(w, err)
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
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) update(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, msg := decodeBook(r)
	if msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}
	b.ID = id
	if err := a.store.Update(b); errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(id); errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
