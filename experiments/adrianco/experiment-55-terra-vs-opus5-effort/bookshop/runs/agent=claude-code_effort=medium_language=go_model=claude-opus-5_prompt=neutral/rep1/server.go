package main

import (
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
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

// ---- handlers ----

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	if err := s.store.Ping(); err != nil {
		s.writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status": "unhealthy",
			"error":  "database unreachable",
		})
		return
	}
	s.writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	book, err := in.toBook()
	if err != nil {
		s.writeError(w, err)
		return
	}
	created, err := s.store.Create(book)
	if err != nil {
		s.writeError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(created.ID, 10))
	s.writeJSON(w, http.StatusCreated, created)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.URL.Query().Get("author"))
	if err != nil {
		s.writeError(w, err)
		return
	}
	s.writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(id)
	if err != nil {
		s.writeError(w, err)
		return
	}
	s.writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	book, err := in.toBook()
	if err != nil {
		s.writeError(w, err)
		return
	}
	updated, err := s.store.Update(id, book)
	if err != nil {
		s.writeError(w, err)
		return
	}
	s.writeJSON(w, http.StatusOK, updated)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(id); err != nil {
		s.writeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// ---- helpers ----

const maxBodyBytes = 1 << 20 // 1 MiB

func (s *Server) decodeInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		msg := "request body must be a valid JSON object"
		if errors.Is(err, io.EOF) {
			msg = "request body must not be empty"
		}
		s.writeJSON(w, http.StatusBadRequest, errBody(msg, nil))
		return BookInput{}, false
	}
	return in, true
}

func (s *Server) pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		s.writeJSON(w, http.StatusBadRequest, errBody("id must be a positive integer", nil))
		return 0, false
	}
	return id, true
}

func (s *Server) writeError(w http.ResponseWriter, err error) {
	var ve *ValidationError
	switch {
	case errors.As(err, &ve):
		s.writeJSON(w, http.StatusBadRequest, errBody("validation failed", ve.Fields))
	case errors.Is(err, ErrNotFound):
		s.writeJSON(w, http.StatusNotFound, errBody("book not found", nil))
	default:
		s.log.Error("unhandled request error", "err", err)
		s.writeJSON(w, http.StatusInternalServerError, errBody("internal server error", nil))
	}
}

func errBody(msg string, fields map[string]string) map[string]any {
	body := map[string]any{"error": msg}
	if len(fields) > 0 {
		body["fields"] = fields
	}
	return body
}

func (s *Server) writeJSON(w http.ResponseWriter, status int, payload any) {
	buf, err := json.Marshal(payload)
	if err != nil {
		s.log.Error("marshal response", "err", err)
		http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if _, err := w.Write(buf); err != nil {
		s.log.Warn("write response", "err", err)
	}
}
