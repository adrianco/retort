package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
)

const maxBodyBytes = 1 << 20

// NewHandler returns the HTTP handler serving the books API.
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

type api struct {
	store *Store
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (a *api) serverError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// decodeBook parses and validates a request body into a Book.
func decodeBook(r *http.Request) (*Book, string) {
	dec := json.NewDecoder(http.MaxBytesReader(nil, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	var in struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}
	if err := dec.Decode(&in); err != nil {
		return nil, "invalid JSON body: " + err.Error()
	}
	if err := dec.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return nil, "invalid JSON body: unexpected trailing data"
	}
	b := &Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}
	switch {
	case b.Title == "":
		return nil, "title is required"
	case b.Author == "":
		return nil, "author is required"
	case b.Year < 0:
		return nil, "year must not be negative"
	}
	return b, ""
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(); err != nil {
		log.Printf("health check: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) create(w http.ResponseWriter, r *http.Request) {
	b, msg := decodeBook(r)
	if msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return
	}
	if err := a.store.Create(b); err != nil {
		a.serverError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (a *api) list(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.URL.Query().Get("author"))
	if err != nil {
		a.serverError(w, err)
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
	}
	if err != nil {
		a.serverError(w, err)
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
	err := a.store.Update(b)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		a.serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	err := a.store.Delete(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		a.serverError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
