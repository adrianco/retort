package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// Server holds dependencies and exposes the HTTP handler.
type Server struct {
	store *Store
	mux   *http.ServeMux
}

// NewServer wires up the routes.
func NewServer(store *Store) *Server {
	s := &Server{store: store, mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) routes() {
	s.mux.HandleFunc("/health", s.handleHealth)
	s.mux.HandleFunc("/books", s.handleBooks)
	s.mux.HandleFunc("/books/", s.handleBookByID)
}

// ServeHTTP makes Server an http.Handler.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// handleBooks serves the collection endpoints: GET (list) and POST (create).
func (s *Server) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		books, err := s.store.List(r.URL.Query().Get("author"))
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, books)
	case http.MethodPost:
		in, ok := decodeInput(w, r)
		if !ok {
			return
		}
		book, err := s.store.Create(in)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusCreated, book)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// handleBookByID serves single-resource endpoints: GET, PUT, DELETE.
func (s *Server) handleBookByID(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || idStr == "" {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}

	switch r.Method {
	case http.MethodGet:
		book, err := s.store.Get(id)
		if handleStoreErr(w, err) {
			return
		}
		writeJSON(w, http.StatusOK, book)
	case http.MethodPut:
		in, ok := decodeInput(w, r)
		if !ok {
			return
		}
		book, err := s.store.Update(id, in)
		if handleStoreErr(w, err) {
			return
		}
		writeJSON(w, http.StatusOK, book)
	case http.MethodDelete:
		err := s.store.Delete(id)
		if handleStoreErr(w, err) {
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// decodeInput parses and validates a book payload, writing an error response on failure.
func decodeInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return bookInput{}, false
	}
	if errs := in.validate(); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{"errors": errs})
		return bookInput{}, false
	}
	return in, true
}

// handleStoreErr writes an appropriate response for store errors. Returns true if handled.
func handleStoreErr(w http.ResponseWriter, err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return true
	}
	writeError(w, http.StatusInternalServerError, err.Error())
	return true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
