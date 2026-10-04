package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// maxBodyBytes caps request bodies; book records are small.
const maxBodyBytes = 1 << 20

// NewHandler returns the HTTP handler exposing the book API backed by store.
func NewHandler(store *Store) http.Handler {
	a := &api{store: store}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.createBook)
	mux.HandleFunc("GET /books", a.listBooks)
	mux.HandleFunc("GET /books/{id}", a.getBook)
	mux.HandleFunc("PUT /books/{id}", a.updateBook)
	mux.HandleFunc("DELETE /books/{id}", a.deleteBook)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// An empty pattern means no route matched; replace the mux's
		// plain-text 404/405 with a JSON error.
		if h, pattern := mux.Handler(r); pattern == "" {
			sw := &statusWriter{header: w.Header()}
			h.ServeHTTP(sw, r)
			writeError(w, sw.status, strings.ToLower(http.StatusText(sw.status)))
			return
		}
		mux.ServeHTTP(w, r)
	})
}

// statusWriter records the status code and discards the body. Headers (such
// as Allow) are set directly on the underlying response.
type statusWriter struct {
	header http.Header
	status int
}

func (s *statusWriter) Header() http.Header         { return s.header }
func (s *statusWriter) Write(b []byte) (int, error) { return len(b), nil }
func (s *statusWriter) WriteHeader(status int)      { s.status = status }

type api struct {
	store *Store
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(r.Context()); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *api) createBook(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	if err := a.store.Create(r.Context(), &b); err != nil {
		writeInternalError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (a *api) listBooks(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.Context(), strings.TrimSpace(r.URL.Query().Get("author")))
	if err != nil {
		writeInternalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *api) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := a.store.Get(r.Context(), id)
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b.ID = id
	if err := a.store.Update(r.Context(), b); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *api) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(r.Context(), id); err != nil {
		writeStoreError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// parseID extracts the {id} path value, writing a 400 response if it is not
// a positive integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

// decodeBook reads and validates a book from the request body, writing an
// error response and returning false if it is malformed or invalid.
func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var in struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
			return Book{}, false
		}
		writeError(w, http.StatusBadRequest, "request body must be valid JSON with title, author, year (number) and isbn")
		return Book{}, false
	}

	b := Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}
	var problems []string
	if b.Title == "" {
		problems = append(problems, "title is required")
	}
	if b.Author == "" {
		problems = append(problems, "author is required")
	}
	if b.Year < 0 {
		problems = append(problems, "year must not be negative")
	}
	if len(problems) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":   "validation failed",
			"details": problems,
		})
		return Book{}, false
	}
	return b, true
}

func writeStoreError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeInternalError(w, err)
}

func writeInternalError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}
