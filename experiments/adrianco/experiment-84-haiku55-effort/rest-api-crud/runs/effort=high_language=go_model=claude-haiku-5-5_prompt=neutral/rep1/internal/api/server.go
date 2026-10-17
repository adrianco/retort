// Package api exposes the book collection over a JSON REST API.
package api

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"

	"bookservice/internal/book"
	"bookservice/internal/store"
)

// maxBodyBytes caps request bodies so a client cannot exhaust memory.
const maxBodyBytes = 1 << 20

// Server holds the dependencies for the HTTP handlers.
type Server struct {
	store *store.Store
}

// NewHandler returns the HTTP handler for the book API.
func NewHandler(s *store.Store) http.Handler {
	srv := &Server{store: s}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", srv.health)
	mux.HandleFunc("POST /books", srv.createBook)
	mux.HandleFunc("GET /books", srv.listBooks)
	mux.HandleFunc("GET /books/{id}", srv.getBook)
	mux.HandleFunc("PUT /books/{id}", srv.updateBook)
	mux.HandleFunc("DELETE /books/{id}", srv.deleteBook)

	// Catch-alls for paths and methods not handled above, so every error
	// response is JSON. The method-specific patterns above take precedence.
	mux.HandleFunc("/books", methodNotAllowed("GET, POST"))
	mux.HandleFunc("/books/{id}", methodNotAllowed("GET, PUT, DELETE"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "not found")
	})
	return mux
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		log.Printf("health check failed: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	if err := s.store.Create(r.Context(), &b); err != nil {
		serverError(w, "create book", err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))

	books, err := s.store.List(r.Context(), author)
	if err != nil {
		serverError(w, "list books", err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(r.Context(), id)
	if errors.Is(err, store.ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		serverError(w, "get book", err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

// updateBook replaces the book's fields. PUT is a full replacement, so the
// body must satisfy the same validation rules as create.
func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b.ID = id
	if err := s.store.Update(r.Context(), b); errors.Is(err, store.ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverError(w, "update book", err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	err := s.store.Delete(r.Context(), id)
	if errors.Is(err, store.ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		serverError(w, "delete book", err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBook parses and validates a book from the request body. On failure it
// writes the error response and returns false. Unknown JSON fields (including
// a client-supplied "id") are ignored; the server always assigns ids.
func decodeBook(w http.ResponseWriter, r *http.Request) (book.Book, bool) {
	var in struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(&in); err != nil {
		var tooLarge *http.MaxBytesError
		switch {
		case errors.As(err, &tooLarge):
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large")
		case errors.Is(err, io.EOF):
			writeError(w, http.StatusBadRequest, "request body must be a JSON object")
		default:
			writeError(w, http.StatusBadRequest, "malformed JSON: "+err.Error())
		}
		return book.Book{}, false
	}
	// Reject trailing content such as a second JSON document.
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return book.Book{}, false
	}

	b := book.Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
	if err := book.Validate(&b); err != nil {
		var ve *book.ValidationError
		if errors.As(err, &ve) {
			writeJSON(w, http.StatusBadRequest, map[string]any{
				"error":   err.Error(),
				"details": ve.Details,
			})
		} else {
			serverError(w, "validate book", err)
		}
		return book.Book{}, false
	}
	return b, true
}

// pathID parses the {id} path segment as a positive integer.
func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func methodNotAllowed(allow string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func serverError(w http.ResponseWriter, op string, err error) {
	log.Printf("%s: %v", op, err)
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
