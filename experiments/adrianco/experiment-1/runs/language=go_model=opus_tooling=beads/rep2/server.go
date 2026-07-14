package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

type Server struct {
	store *Store
	mux   *http.ServeMux
}

func NewServer(store *Store) *Server {
	s := &Server{store: store, mux: http.NewServeMux()}
	s.mux.HandleFunc("/health", s.health)
	s.mux.HandleFunc("/books", s.books)
	s.mux.HandleFunc("/books/", s.bookByID)
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) { s.mux.ServeHTTP(w, r) }

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		books, err := s.store.List(r.URL.Query().Get("author"))
		if err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, books)
	case http.MethodPost:
		var b Book
		if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
			writeErr(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if strings.TrimSpace(b.Title) == "" || strings.TrimSpace(b.Author) == "" {
			writeErr(w, http.StatusBadRequest, "title and author are required")
			return
		}
		if err := s.store.Create(&b); err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusCreated, b)
	default:
		writeErr(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *Server) bookByID(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	if idStr == "" || strings.Contains(idStr, "/") {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "invalid id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := s.store.Get(id)
		if errors.Is(err, ErrNotFound) {
			writeErr(w, http.StatusNotFound, "book not found")
			return
		}
		if err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, b)
	case http.MethodPut:
		var b Book
		if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
			writeErr(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if strings.TrimSpace(b.Title) == "" || strings.TrimSpace(b.Author) == "" {
			writeErr(w, http.StatusBadRequest, "title and author are required")
			return
		}
		if err := s.store.Update(id, &b); errors.Is(err, ErrNotFound) {
			writeErr(w, http.StatusNotFound, "book not found")
			return
		} else if err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, b)
	case http.MethodDelete:
		if err := s.store.Delete(id); errors.Is(err, ErrNotFound) {
			writeErr(w, http.StatusNotFound, "book not found")
			return
		} else if err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		writeErr(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}
