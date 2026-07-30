package main

import (
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
)

// Server wires the HTTP routes to the store.
type Server struct {
	store *Store
	log   *slog.Logger
	mux   *http.ServeMux
}

// NewServer builds a Server with all routes registered.
func NewServer(store *Store, log *slog.Logger) *Server {
	s := &Server{store: store, log: log, mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) routes() {
	s.mux.HandleFunc("GET /health", s.handleHealth)
	s.mux.HandleFunc("POST /books", s.handleCreate)
	s.mux.HandleFunc("GET /books", s.handleList)
	s.mux.HandleFunc("GET /books/{id}", s.handleGet)
	s.mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	s.mux.HandleFunc("DELETE /books/{id}", s.handleDelete)
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

// maxBodyBytes caps request payloads so a malformed client cannot exhaust memory.
const maxBodyBytes = 1 << 20 // 1 MiB

// errorResponse is the JSON envelope for every non-2xx response.
type errorResponse struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		s.log.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status":   "unavailable",
			"database": "unreachable",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status":   "ok",
		"database": "ok",
	})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	book, err := in.Validate()
	if err != nil {
		s.writeError(w, err)
		return
	}
	created, err := s.store.Create(r.Context(), book)
	if err != nil {
		s.writeError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		s.writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"books": books,
		"count": len(books),
	})
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := s.parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := s.parseID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	// PUT replaces the resource, so the payload must be complete and valid on
	// its own rather than merging with what is already stored.
	book, err := in.Validate()
	if err != nil {
		s.writeError(w, err)
		return
	}
	updated, err := s.store.Update(r.Context(), id, book)
	if err != nil {
		s.writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := s.parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.writeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// parseID reads the {id} path value, writing a 400 and reporting false if it is
// not a positive integer.
func (s *Server) parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		writeJSON(w, http.StatusBadRequest, errorResponse{
			Error: "invalid book id: " + raw,
		})
		return 0, false
	}
	return id, true
}

// decodeInput reads a JSON BookInput from the request body, writing a 400 and
// reporting false on any problem.
func (s *Server) decodeInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	if ct := r.Header.Get("Content-Type"); ct != "" {
		if mediaType := strings.TrimSpace(strings.Split(ct, ";")[0]); mediaType != "application/json" {
			writeJSON(w, http.StatusUnsupportedMediaType, errorResponse{
				Error: "Content-Type must be application/json",
			})
			return BookInput{}, false
		}
	}

	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()

	var in BookInput
	if err := dec.Decode(&in); err != nil {
		msg := "request body must be valid JSON"
		if errors.Is(err, io.EOF) {
			msg = "request body is required"
		} else {
			msg = "invalid request body: " + err.Error()
		}
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: msg})
		return BookInput{}, false
	}
	// Reject trailing content so "{} {}" is not silently accepted.
	if err := dec.Decode(new(json.RawMessage)); !errors.Is(err, io.EOF) {
		writeJSON(w, http.StatusBadRequest, errorResponse{
			Error: "request body must contain a single JSON object",
		})
		return BookInput{}, false
	}
	return in, true
}

// writeError maps a domain error to the matching status code and JSON body.
func (s *Server) writeError(w http.ResponseWriter, err error) {
	var vErr *validationError
	switch {
	case errors.As(err, &vErr):
		writeJSON(w, http.StatusBadRequest, errorResponse{
			Error:  "validation failed",
			Fields: vErr.Fields,
		})
	case errors.Is(err, ErrNotFound):
		writeJSON(w, http.StatusNotFound, errorResponse{Error: ErrNotFound.Error()})
	case errors.Is(err, ErrDuplicateISBN):
		writeJSON(w, http.StatusConflict, errorResponse{Error: ErrDuplicateISBN.Error()})
	default:
		// Unexpected failures are logged in full but reported opaquely.
		s.log.Error("request failed", "error", err)
		writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "internal server error"})
	}
}

// writeJSON serialises v as the response body with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	body, err := json.Marshal(v)
	if err != nil {
		http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	body = append(body, '\n')
	_, _ = w.Write(body)
}
