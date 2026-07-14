package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
)

func newRouter(s store) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handleHealth)
	mux.HandleFunc("POST /books", handleCreateBook(s))
	mux.HandleFunc("GET /books", handleListBooks(s))
	mux.HandleFunc("GET /books/{id}", handleGetBook(s))
	mux.HandleFunc("PUT /books/{id}", handleUpdateBook(s))
	mux.HandleFunc("DELETE /books/{id}", handleDeleteBook(s))
	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func parseID(r *http.Request) (int64, error) {
	return strconv.ParseInt(r.PathValue("id"), 10, 64)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func handleCreateBook(s store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var b Book
		if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if b.Title == "" || b.Author == "" {
			writeError(w, http.StatusBadRequest, "title and author are required")
			return
		}
		created, err := s.create(b)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to create book")
			return
		}
		writeJSON(w, http.StatusCreated, created)
	}
}

func handleListBooks(s store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		author := r.URL.Query().Get("author")
		books, err := s.list(author)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to list books")
			return
		}
		writeJSON(w, http.StatusOK, books)
	}
}

func handleGetBook(s store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := parseID(r)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid id")
			return
		}
		book, err := s.get(id)
		if errors.Is(err, errNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to get book")
			return
		}
		writeJSON(w, http.StatusOK, book)
	}
}

func handleUpdateBook(s store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := parseID(r)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid id")
			return
		}
		var b Book
		if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if b.Title == "" || b.Author == "" {
			writeError(w, http.StatusBadRequest, "title and author are required")
			return
		}
		updated, err := s.update(id, b)
		if errors.Is(err, errNotFound) {
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

func handleDeleteBook(s store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := parseID(r)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid id")
			return
		}
		err = s.delete(id)
		if errors.Is(err, errNotFound) {
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
