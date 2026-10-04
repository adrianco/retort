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

// NewHandler wires the HTTP routes to the store.
func NewHandler(store *Store) http.Handler {
	a := &api{store: store}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
	return mux
}

type api struct {
	store *Store
}

// bookInput is the request body for create and update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate trims the input and returns field -> message for each problem.
func (in *bookInput) validate() map[string]string {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	errs := map[string]string{}
	if in.Title == "" {
		errs["title"] = "title is required"
	}
	if in.Author == "" {
		errs["author"] = "author is required"
	}
	if in.Year < 0 {
		errs["year"] = "year must not be negative"
	}
	return errs
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b := Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
	if err := a.store.Create(&b); err != nil {
		serverError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *api) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := a.store.Get(id)
	if err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b := Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
	if err := a.store.Update(b); err != nil {
		storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(id); err != nil {
		storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBook parses and validates the request body, writing the error
// response itself when it returns false.
func decodeBook(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var tooBig *http.MaxBytesError
		if errors.As(err, &tooBig) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large", nil)
			return in, false
		}
		writeError(w, http.StatusBadRequest, "request body must be a valid JSON book object", nil)
		return in, false
	}
	if _, err := dec.Token(); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object", nil)
		return in, false
	}
	if errs := in.validate(); len(errs) > 0 {
		writeError(w, http.StatusBadRequest, "validation failed", errs)
		return in, false
	}
	return in, true
}

func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer", nil)
		return 0, false
	}
	return id, true
}

func storeError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found", nil)
		return
	}
	serverError(w, err)
}

func serverError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error", nil)
}

type errorBody struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string, fields map[string]string) {
	writeJSON(w, status, errorBody{Error: msg, Fields: fields})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}
