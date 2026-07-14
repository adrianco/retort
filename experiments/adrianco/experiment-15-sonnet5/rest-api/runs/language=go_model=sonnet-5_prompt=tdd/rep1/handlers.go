package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// NewRouter builds the HTTP handler for the book collection API.
func NewRouter(s *Store) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", handleHealth)
	mux.HandleFunc("POST /books", handleCreateBook(s))
	mux.HandleFunc("GET /books", handleListBooks(s))
	mux.HandleFunc("GET /books/{id}", handleGetBook(s))
	mux.HandleFunc("PUT /books/{id}", handleUpdateBook(s))
	mux.HandleFunc("DELETE /books/{id}", handleDeleteBook(s))

	return mux
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func handleCreateBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var b Book
		if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}
		if err := validateBook(b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}

		created, err := s.CreateBook(b)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to create book")
			return
		}
		writeJSON(w, http.StatusCreated, created)
	}
}

func handleListBooks(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		author := r.URL.Query().Get("author")
		books, err := s.ListBooks(author)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to list books")
			return
		}
		writeJSON(w, http.StatusOK, books)
	}
}

func handleGetBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid book id")
			return
		}

		b, err := s.GetBook(id)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to get book")
			return
		}
		writeJSON(w, http.StatusOK, b)
	}
}

func handleUpdateBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid book id")
			return
		}

		var b Book
		if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}
		if err := validateBook(b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}

		updated, err := s.UpdateBook(id, b)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to update book")
			return
		}
		writeJSON(w, http.StatusOK, updated)
	}
}

func handleDeleteBook(s *Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid book id")
			return
		}

		err = s.DeleteBook(id)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to delete book")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}
}

func validateBook(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return errors.New("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return errors.New("author is required")
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
