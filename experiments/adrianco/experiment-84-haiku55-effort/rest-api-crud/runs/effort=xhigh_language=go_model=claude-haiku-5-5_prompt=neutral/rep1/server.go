package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
)

const maxBodyBytes = 1 << 20 // 1 MiB

// NewHandler returns the HTTP API backed by store.
func NewHandler(store *Store) http.Handler {
	s := &server{store: store}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	// Requests that match no route above land here, so they also get JSON errors.
	mux.HandleFunc("/", s.fallback)
	return mux
}

type server struct {
	store *Store
}

type errorBody struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		log.Printf("health: database unreachable: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	var body BookInput
	if !decodeBody(w, r, &body) {
		return
	}
	in, ok := normalizeOrReject(w, body)
	if !ok {
		return
	}

	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		fail(w, r, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// updateBook replaces the whole book. Fields left out of the body are cleared.
func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	var body BookInput
	if !decodeBody(w, r, &body) {
		return
	}
	in, ok := normalizeOrReject(w, body)
	if !ok {
		return
	}

	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		fail(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// fallback answers requests no route matched. A known path with the wrong method gets 405
// and an Allow header. Anything else gets 404.
func (s *server) fallback(w http.ResponseWriter, r *http.Request) {
	allow := allowedMethods(r.URL.Path)
	if allow == "" {
		writeError(w, http.StatusNotFound, "not found")
		return
	}
	w.Header().Set("Allow", allow)
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func allowedMethods(path string) string {
	switch {
	case path == "/health":
		return "GET"
	case path == "/books":
		return "GET, POST"
	case strings.HasPrefix(path, "/books/") && path != "/books/" && !strings.Contains(path[len("/books/"):], "/"):
		return "GET, PUT, DELETE"
	}
	return ""
}

// parseID reads the {id} path value. It writes a 400 and returns false if it is not a positive integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return 0, false
	}
	return id, true
}

// normalizeOrReject validates the input. On failure it writes a 400 listing the bad fields.
func normalizeOrReject(w http.ResponseWriter, body BookInput) (BookInput, bool) {
	in, problems := body.Normalize()
	if len(problems) > 0 {
		writeJSON(w, http.StatusBadRequest, errorBody{Error: "validation failed", Fields: problems})
		return BookInput{}, false
	}
	return in, true
}

// decodeBody reads one JSON object from the request body into v. It rejects unknown fields,
// trailing data and bodies over maxBodyBytes, and writes the error response when it returns false.
func decodeBody(w http.ResponseWriter, r *http.Request, v any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()

	if err := dec.Decode(v); err != nil {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		} else {
			writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		}
		return false
	}
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return false
	}
	return true
}

// fail maps a store error to a response. Missing books become 404. Anything else is logged and becomes 500.
func fail(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, ErrNotFound.Error())
		return
	}
	log.Printf("%s %s: %v", r.Method, r.URL.Path, err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorBody{Error: msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}
