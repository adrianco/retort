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

const (
	maxBodyBytes = 1 << 20
	maxYear      = 9999
)

// Server exposes the book collection over HTTP.
type Server struct {
	store *Store
}

// NewServer returns a Server backed by store.
func NewServer(store *Store) *Server {
	return &Server{store: store}
}

// Handler returns the routed HTTP handler for the API.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreate)
	mux.HandleFunc("GET /books", s.handleList)
	mux.HandleFunc("GET /books/{id}", s.handleGet)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	mux.HandleFunc("DELETE /books/{id}", s.handleDelete)
	return jsonErrors(mux)
}

// bookInput is the request body accepted by create and update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate normalises the input and returns a message per invalid field.
func (in *bookInput) validate() map[string]string {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	fields := map[string]string{}
	if in.Title == "" {
		fields["title"] = "title is required"
	}
	if in.Author == "" {
		fields["author"] = "author is required"
	}
	if in.Year < 0 || in.Year > maxYear {
		fields["year"] = "year must be between 0 and " + strconv.Itoa(maxYear)
	}
	return fields
}

func (in bookInput) book() Book {
	return Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		log.Printf("health: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), in.book())
	if err != nil {
		writeStoreError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(book.ID, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBook(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, in.book())
	if err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		writeStoreError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// parseID reads the {id} path value, writing a 400 if it is not a positive
// integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

// decodeBook reads and validates a book from the request body, writing the
// error response itself when the body is unusable.
func decodeBook(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := dec.Decode(&in); err != nil {
		var tooLarge *http.MaxBytesError
		var typeErr *json.UnmarshalTypeError
		switch {
		case errors.As(err, &tooLarge):
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		case errors.As(err, &typeErr) && typeErr.Field != "":
			writeError(w, http.StatusBadRequest, "field "+strconv.Quote(typeErr.Field)+" has the wrong type")
		default:
			writeError(w, http.StatusBadRequest, "request body must be a valid JSON object")
		}
		return in, false
	}
	if _, err := dec.Token(); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return in, false
	}
	if fields := in.validate(); len(fields) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":  "validation failed",
			"fields": fields,
		})
		return in, false
	}
	return in, true
}

func writeStoreError(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	log.Printf("store: %v", err)
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

// jsonErrors rewrites the mux's plain-text 404 and 405 responses as JSON so
// every response from the API has the same shape.
func jsonErrors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		next.ServeHTTP(&jsonErrorWriter{ResponseWriter: w}, r)
	})
}

type jsonErrorWriter struct {
	http.ResponseWriter
	intercepted bool
}

func (w *jsonErrorWriter) WriteHeader(status int) {
	isJSON := strings.HasPrefix(w.Header().Get("Content-Type"), "application/json")
	if !isJSON && (status == http.StatusNotFound || status == http.StatusMethodNotAllowed) {
		w.intercepted = true
		w.Header().Del("X-Content-Type-Options")
		writeError(w.ResponseWriter, status, strings.ToLower(http.StatusText(status)))
		return
	}
	w.ResponseWriter.WriteHeader(status)
}

func (w *jsonErrorWriter) Write(p []byte) (int, error) {
	if w.intercepted {
		// Drop the mux's plain-text body; the JSON one is already written.
		return len(p), nil
	}
	return w.ResponseWriter.Write(p)
}
