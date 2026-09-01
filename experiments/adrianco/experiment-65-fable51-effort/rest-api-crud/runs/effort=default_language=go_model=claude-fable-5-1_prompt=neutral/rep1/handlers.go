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
	"time"
)

const maxBodyBytes = 1 << 20 // 1 MiB

// Server holds the HTTP handlers and their dependencies.
type Server struct {
	store *Store
	log   *log.Logger
}

// NewServer wires the store into an HTTP handler.
func NewServer(store *Store, logger *log.Logger) *Server {
	if logger == nil {
		logger = log.Default()
	}
	return &Server{store: store, log: logger}
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
	return s.logRequests(mux)
}

func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.log.Printf("%s %s -> %d (%s)", r.Method, r.URL.RequestURI(), rec.status, time.Since(start).Round(time.Microsecond))
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

// --- responses ---------------------------------------------------------------

type errorResponse struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details,omitempty"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if v != nil {
		_ = json.NewEncoder(w).Encode(v)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func writeValidationError(w http.ResponseWriter, details map[string]string) {
	writeJSON(w, http.StatusUnprocessableEntity, errorResponse{Error: "validation failed", Details: details})
}

// --- input handling ----------------------------------------------------------

func decodeBookInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	if ct := r.Header.Get("Content-Type"); ct != "" && !strings.HasPrefix(ct, "application/json") {
		writeError(w, http.StatusUnsupportedMediaType, "Content-Type must be application/json")
		return in, false
	}
	dec := json.NewDecoder(io.LimitReader(r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return in, false
	}
	if dec.More() {
		writeError(w, http.StatusBadRequest, "invalid JSON body: unexpected trailing data")
		return in, false
	}
	return in, true
}

// validated holds the cleaned fields after validation succeeds.
type validated struct {
	title  string
	author string
	year   *int
	isbn   string
}

func validateBookInput(in BookInput) (validated, map[string]string) {
	details := map[string]string{}
	var v validated

	if in.Title == nil || strings.TrimSpace(*in.Title) == "" {
		details["title"] = "is required"
	} else {
		v.title = strings.TrimSpace(*in.Title)
		if len(v.title) > 500 {
			details["title"] = "must be at most 500 characters"
		}
	}

	if in.Author == nil || strings.TrimSpace(*in.Author) == "" {
		details["author"] = "is required"
	} else {
		v.author = strings.TrimSpace(*in.Author)
		if len(v.author) > 200 {
			details["author"] = "must be at most 200 characters"
		}
	}

	if in.Year != nil {
		maxYear := time.Now().Year() + 1
		if *in.Year < 0 || *in.Year > maxYear {
			details["year"] = fmt.Sprintf("must be between 0 and %d", maxYear)
		} else {
			y := *in.Year
			v.year = &y
		}
	}

	if in.ISBN != nil {
		isbn := normalizeISBN(*in.ISBN)
		if isbn != "" && !validISBN(isbn) {
			details["isbn"] = "must be a valid ISBN-10 or ISBN-13"
		} else {
			v.isbn = isbn
		}
	}

	if len(details) > 0 {
		return validated{}, details
	}
	return v, nil
}

// normalizeISBN strips hyphens and spaces and upper-cases a trailing X.
func normalizeISBN(s string) string {
	var b strings.Builder
	for _, r := range strings.TrimSpace(s) {
		if r == '-' || r == ' ' {
			continue
		}
		b.WriteRune(r)
	}
	return strings.ToUpper(b.String())
}

// validISBN checks the ISBN-10 or ISBN-13 checksum of an already-normalized string.
func validISBN(s string) bool {
	switch len(s) {
	case 10:
		sum := 0
		for i, r := range s {
			var d int
			switch {
			case r >= '0' && r <= '9':
				d = int(r - '0')
			case r == 'X' && i == 9:
				d = 10
			default:
				return false
			}
			sum += d * (10 - i)
		}
		return sum%11 == 0
	case 13:
		sum := 0
		for i, r := range s {
			if r < '0' || r > '9' {
				return false
			}
			d := int(r - '0')
			if i%2 == 1 {
				d *= 3
			}
			sum += d
		}
		return sum%10 == 0
	default:
		return false
	}
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func (s *Server) storeError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found")
	case errors.Is(err, ErrDuplicateISBN):
		writeJSON(w, http.StatusConflict, errorResponse{Error: "conflict", Details: map[string]string{"isbn": "already exists"}})
	default:
		s.log.Printf("internal error: %v", err)
		writeError(w, http.StatusInternalServerError, "internal server error")
	}
}

// --- handlers ----------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unhealthy", "database": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "database": "ok"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	v, details := validateBookInput(in)
	if details != nil {
		writeValidationError(w, details)
		return
	}
	book, err := s.store.Create(r.Context(), v.title, v.author, v.year, v.isbn)
	if err != nil {
		s.storeError(w, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.storeError(w, err)
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
		s.storeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}
	v, details := validateBookInput(in)
	if details != nil {
		writeValidationError(w, details)
		return
	}
	book, err := s.store.Update(r.Context(), id, v.title, v.author, v.year, v.isbn)
	if err != nil {
		s.storeError(w, err)
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
		s.storeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
