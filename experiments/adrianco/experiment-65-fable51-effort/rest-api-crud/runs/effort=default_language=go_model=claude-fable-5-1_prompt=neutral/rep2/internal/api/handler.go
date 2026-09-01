// Package api exposes the book collection over HTTP/JSON.
package api

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"

	"bookapi/internal/store"
)

const maxBodyBytes = 1 << 20 // 1 MiB

// Store is the persistence interface the API depends on.
type Store interface {
	Ping(ctx context.Context) error
	Create(ctx context.Context, b store.Book) (store.Book, error)
	Get(ctx context.Context, id int64) (store.Book, error)
	List(ctx context.Context, author string) ([]store.Book, error)
	Update(ctx context.Context, id int64, b store.Book) (store.Book, error)
	Delete(ctx context.Context, id int64) error
}

// Server holds the HTTP handlers and their dependencies.
type Server struct {
	store  Store
	logger *slog.Logger
}

// New builds a Server backed by st.
func New(st Store, logger *slog.Logger) *Server {
	if logger == nil {
		logger = slog.Default()
	}
	return &Server{store: st, logger: logger}
}

// Handler returns the fully routed HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.health)
	mux.HandleFunc("POST /books", s.createBook)
	mux.HandleFunc("GET /books", s.listBooks)
	mux.HandleFunc("GET /books/{id}", s.getBook)
	mux.HandleFunc("PUT /books/{id}", s.updateBook)
	mux.HandleFunc("DELETE /books/{id}", s.deleteBook)
	return s.logRequests(mux)
}

// bookInput is the request body accepted by POST and PUT.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate normalises and checks the input, returning field-level errors.
func (in *bookInput) validate() map[string]string {
	problems := map[string]string{}
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	if in.Title == "" {
		problems["title"] = "title is required"
	} else if len(in.Title) > 500 {
		problems["title"] = "title must be at most 500 characters"
	}
	if in.Author == "" {
		problems["author"] = "author is required"
	} else if len(in.Author) > 200 {
		problems["author"] = "author must be at most 200 characters"
	}
	if in.Year != nil {
		maxYear := time.Now().Year() + 1
		if *in.Year < 0 || *in.Year > maxYear {
			problems["year"] = "year must be between 0 and " + strconv.Itoa(maxYear)
		}
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		problems["isbn"] = "isbn must be a 10 or 13 digit ISBN (hyphens allowed)"
	}
	return problems
}

// validISBN accepts ISBN-10 and ISBN-13 forms, ignoring hyphens and spaces.
// ISBN-10 may end in an 'X' check digit.
func validISBN(s string) bool {
	clean := strings.NewReplacer("-", "", " ", "").Replace(s)
	switch len(clean) {
	case 10:
		for i, r := range clean {
			if r >= '0' && r <= '9' {
				continue
			}
			if i == 9 && (r == 'X' || r == 'x') {
				continue
			}
			return false
		}
		return true
	case 13:
		for _, r := range clean {
			if r < '0' || r > '9' {
				return false
			}
		}
		return true
	default:
		return false
	}
}

func (in bookInput) toBook() store.Book {
	return store.Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}

// --- handlers ---

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status": "unhealthy", "database": "unreachable",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "database": "ok"})
}

func (s *Server) createBook(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeBook(w, r)
	if !ok {
		return
	}
	b, err := s.store.Create(r.Context(), in.toBook())
	if err != nil {
		s.storeError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *Server) listBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) getBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) updateBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeBook(w, r)
	if !ok {
		return
	}
	b, err := s.store.Update(r.Context(), id, in.toBook())
	if err != nil {
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// --- helpers ---

// decodeBook parses and validates a JSON book body. On failure it writes the
// error response and returns ok=false.
func (s *Server) decodeBook(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		var maxErr *http.MaxBytesError
		switch {
		case errors.As(err, &maxErr):
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large", nil)
		case errors.Is(err, io.EOF):
			writeError(w, http.StatusBadRequest, "request body is required", nil)
		default:
			writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error(), nil)
		}
		return in, false
	}
	// Reject trailing garbage after the first JSON value.
	if dec.More() {
		writeError(w, http.StatusBadRequest, "invalid JSON body: unexpected trailing data", nil)
		return in, false
	}
	if problems := in.validate(); len(problems) > 0 {
		writeError(w, http.StatusUnprocessableEntity, "validation failed", problems)
		return in, false
	}
	return in, true
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id", nil)
		return 0, false
	}
	return id, true
}

func (s *Server) storeError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found", nil)
	case errors.Is(err, store.ErrDuplicateISBN):
		writeError(w, http.StatusConflict, err.Error(), nil)
	default:
		s.logger.Error("store error", "err", err)
		writeError(w, http.StatusInternalServerError, "internal server error", nil)
	}
}

type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string, fields map[string]string) {
	writeJSON(w, status, errorResponse{Error: msg, Fields: fields})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// logRequests is a minimal structured access-log middleware.
func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.logger.Info("request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rec.status,
			"duration", time.Since(start),
		)
	})
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}
