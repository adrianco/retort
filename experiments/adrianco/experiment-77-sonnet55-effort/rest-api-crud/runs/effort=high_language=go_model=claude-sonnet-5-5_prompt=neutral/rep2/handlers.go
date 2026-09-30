package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
)

const maxBodyBytes = 1 << 20

// NewHandler builds the HTTP router for the book API.
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

type errorBody struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorBody{Error: msg})
}

func serverError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func (a *api) health(w http.ResponseWriter, r *http.Request) {
	if err := a.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status": "unhealthy", "time": time.Now().UTC().Format(time.RFC3339),
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok", "time": time.Now().UTC().Format(time.RFC3339),
	})
}

// bookInput is the accepted request body for create/update.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// decodeBook parses and validates a request body into a Book (without ID).
// On failure it writes the error response and returns false.
func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var mbe *http.MaxBytesError
		switch {
		case errors.As(err, &mbe):
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		case errors.Is(err, io.EOF):
			writeError(w, http.StatusBadRequest, "request body is empty")
		default:
			writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		}
		return Book{}, false
	}
	if dec.More() {
		writeError(w, http.StatusBadRequest, "invalid JSON: unexpected trailing data")
		return Book{}, false
	}

	var b Book
	fields := map[string]string{}
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
	if b.Title == "" {
		fields["title"] = "is required"
	}
	if b.Author == "" {
		fields["author"] = "is required"
	}
	if b.Year < 0 || b.Year > 9999 {
		fields["year"] = "must be between 0 and 9999"
	}
	if len(fields) > 0 {
		writeJSON(w, http.StatusUnprocessableEntity, errorBody{Error: "validation failed", Fields: fields})
		return Book{}, false
	}
	return b, true
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
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	created, err := a.store.Create(b)
	if err != nil {
		serverError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
}

func (a *api) list(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(strings.TrimSpace(r.URL.Query().Get("author")))
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
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b.ID = id
	updated, err := a.store.Update(b)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
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
