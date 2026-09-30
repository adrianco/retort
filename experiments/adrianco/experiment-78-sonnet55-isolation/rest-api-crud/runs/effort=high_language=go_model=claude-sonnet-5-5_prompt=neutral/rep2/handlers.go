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

// API wires HTTP routes to a Store.
type API struct {
	store *Store
}

// Handler returns the HTTP handler exposing all routes.
func (a *API) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (a *API) serverError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// bookInput is the request payload; pointers detect missing fields.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// decodeBook parses and validates a request body into a Book (without ID).
func decodeBook(r *http.Request) (Book, error) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(nil, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		return Book{}, errors.New("invalid JSON body")
	}
	if _, err := dec.Token(); err != io.EOF {
		return Book{}, errors.New("invalid JSON body")
	}
	var b Book
	if in.Title != nil {
		b.Title = strings.TrimSpace(*in.Title)
	}
	if in.Author != nil {
		b.Author = strings.TrimSpace(*in.Author)
	}
	if in.ISBN != nil {
		b.ISBN = strings.TrimSpace(*in.ISBN)
	}
	if in.Year != nil {
		b.Year = *in.Year
	}
	switch {
	case b.Title == "":
		return Book{}, errors.New("title is required")
	case b.Author == "":
		return Book{}, errors.New("author is required")
	case b.Year < 0 || b.Year > 9999:
		return Book{}, errors.New("year must be between 0 and 9999")
	}
	return b, nil
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func (a *API) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) createBook(w http.ResponseWriter, r *http.Request) {
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	created, err := a.store.Create(b)
	if err != nil {
		a.serverError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
}

func (a *API) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.URL.Query().Get("author"))
	if err != nil {
		a.serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := a.store.Get(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		a.serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := decodeBook(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	b.ID = id
	updated, err := a.store.Update(b)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		a.serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (a *API) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(id); errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		a.serverError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
