package bookapi

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
)

// maxBodyBytes caps request bodies to protect the server from oversized input.
const maxBodyBytes = 1 << 20 // 1 MiB

// NewHandler returns the HTTP handler exposing the book API backed by store.
func NewHandler(store *Store) http.Handler {
	s := &server{store: store}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return mux
}

type server struct {
	store *Store
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		slog.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := readBookInput(w, r)
	if !ok {
		return
	}

	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.internalError(w, "create book", err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))

	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.internalError(w, "list books", err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := readID(w, r)
	if !ok {
		return
	}

	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.lookupError(w, "get book", err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := readID(w, r)
	if !ok {
		return
	}
	in, ok := readBookInput(w, r)
	if !ok {
		return
	}

	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.lookupError(w, "update book", err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := readID(w, r)
	if !ok {
		return
	}

	if err := s.store.Delete(r.Context(), id); err != nil {
		s.lookupError(w, "delete book", err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// lookupError maps store errors for single-book operations to HTTP responses.
func (s *server) lookupError(w http.ResponseWriter, op string, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	s.internalError(w, op, err)
}

func (s *server) internalError(w http.ResponseWriter, op string, err error) {
	slog.Error(op+" failed", "err", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

// readID parses the {id} path parameter. It writes a 400 response and returns
// false if the value is not a positive integer.
func readID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

// readBookInput decodes, cleans and validates a book request body. It writes
// a 400 response and returns false on any failure.
func readBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	if err := decodeJSON(w, r, &in); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return BookInput{}, false
	}

	in = in.Clean()
	if err := in.Validate(); err != nil {
		var verr ValidationError
		errors.As(err, &verr)
		writeJSON(w, http.StatusBadRequest, map[string]any{
			"error":  "validation failed",
			"fields": verr,
		})
		return BookInput{}, false
	}
	return in, true
}

// decodeJSON reads exactly one JSON object from the request body, rejecting
// unknown fields and oversized bodies.
func decodeJSON(w http.ResponseWriter, r *http.Request, v any) error {
	body := http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(body)
	dec.DisallowUnknownFields()

	if err := dec.Decode(v); err != nil {
		var maxErr *http.MaxBytesError
		if errors.As(err, &maxErr) {
			return errors.New("request body too large")
		}
		if errors.Is(err, io.EOF) {
			return errors.New("request body is required")
		}
		return fmt.Errorf("invalid JSON body: %v", err)
	}
	if dec.More() {
		return errors.New("request body must contain a single JSON object")
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		slog.Error("encode response", "err", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
