package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"time"
)

const maxBodyBytes = 1 << 20

// bookInput is the request payload for create/update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func (in *bookInput) normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// validate returns field -> message for every invalid field.
func (in bookInput) validate() map[string]string {
	errs := map[string]string{}
	if in.Title == "" {
		errs["title"] = "title is required"
	}
	if in.Author == "" {
		errs["author"] = "author is required"
	}
	if in.Year < 0 || in.Year > time.Now().Year()+1 {
		errs["year"] = "year must be between 0 and next year"
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		errs["isbn"] = "isbn must contain 10 or 13 digits (hyphens/spaces allowed; ISBN-10 may end in X)"
	}
	return errs
}

func validISBN(s string) bool {
	clean := strings.NewReplacer("-", "", " ", "").Replace(s)
	for i, r := range clean {
		isLastX := (r == 'X' || r == 'x') && i == len(clean)-1 && len(clean) == 10
		if (r < '0' || r > '9') && !isLastX {
			return false
		}
	}
	return len(clean) == 10 || len(clean) == 13
}

// NewServer builds the HTTP handler for the API.
func NewServer(store *Store) http.Handler {
	h := &handler{store: store}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("POST /books", h.create)
	mux.HandleFunc("GET /books", h.list)
	mux.HandleFunc("GET /books/{id}", h.get)
	mux.HandleFunc("PUT /books/{id}", h.update)
	mux.HandleFunc("DELETE /books/{id}", h.delete)
	return jsonFallback(mux)
}

// jsonFallback serves the mux's built-in 404/405 responses as JSON instead of
// plain text, while keeping the status code and Allow header the mux chooses.
func jsonFallback(mux *http.ServeMux) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fallback, pattern := mux.Handler(r)
		if pattern != "" {
			mux.ServeHTTP(w, r)
			return
		}
		rec := httptest.NewRecorder()
		fallback.ServeHTTP(rec, r)
		if allow := rec.Header().Get("Allow"); allow != "" {
			w.Header().Set("Allow", allow)
		}
		switch rec.Code {
		case http.StatusMethodNotAllowed:
			writeError(w, rec.Code, "method not allowed")
		case http.StatusNotFound:
			writeError(w, rec.Code, "not found")
		default: // e.g. redirects for path cleaning
			for k, v := range rec.Header() {
				w.Header()[k] = v
			}
			w.WriteHeader(rec.Code)
			w.Write(rec.Body.Bytes())
		}
	})
}

type handler struct {
	store *Store
}

func (h *handler) health(w http.ResponseWriter, r *http.Request) {
	if err := h.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable", "database": "down"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "database": "up"})
}

func (h *handler) create(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeAndValidate(w, r)
	if !ok {
		return
	}
	b, err := h.store.Create(Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
	if err != nil {
		internalError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (h *handler) list(w http.ResponseWriter, r *http.Request) {
	books, err := h.store.List(r.URL.Query().Get("author"))
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (h *handler) get(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := h.store.Get(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handler) update(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeAndValidate(w, r)
	if !ok {
		return
	}
	b, err := h.store.Update(Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN})
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if err != nil {
		internalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handler) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	err := h.store.Delete(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if err != nil {
		internalError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func decodeAndValidate(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return in, false
	}
	if err := dec.Decode(&struct{}{}); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return in, false
	}
	in.normalize()
	if errs := in.validate(); len(errs) > 0 {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]any{"error": "validation failed", "fields": errs})
		return in, false
	}
	return in, true
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

func internalError(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}
