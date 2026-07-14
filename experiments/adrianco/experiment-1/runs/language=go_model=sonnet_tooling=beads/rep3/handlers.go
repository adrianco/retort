package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type errorResponse struct {
	Error string `json:"error"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}

func newRouter(db *sql.DB) http.Handler {
	r := mux.NewRouter()
	r.HandleFunc("/health", handleHealth).Methods(http.MethodGet)
	r.HandleFunc("/books", handleCreateBook(db)).Methods(http.MethodPost)
	r.HandleFunc("/books", handleListBooks(db)).Methods(http.MethodGet)
	r.HandleFunc("/books/{id}", handleGetBook(db)).Methods(http.MethodGet)
	r.HandleFunc("/books/{id}", handleUpdateBook(db)).Methods(http.MethodPut)
	r.HandleFunc("/books/{id}", handleDeleteBook(db)).Methods(http.MethodDelete)
	return r
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func handleCreateBook(db *sql.DB) http.HandlerFunc {
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
		if err := dbCreateBook(db, &b); err != nil {
			writeError(w, http.StatusInternalServerError, "failed to create book")
			return
		}
		writeJSON(w, http.StatusCreated, b)
	}
}

func handleListBooks(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		author := r.URL.Query().Get("author")
		books, err := dbListBooks(db, author)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to list books")
			return
		}
		if books == nil {
			books = []Book{}
		}
		writeJSON(w, http.StatusOK, books)
	}
}

func parseID(r *http.Request) (int64, bool) {
	vars := mux.Vars(r)
	id, err := strconv.ParseInt(vars["id"], 10, 64)
	return id, err == nil
}

func handleGetBook(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(r)
		if !ok {
			writeError(w, http.StatusBadRequest, "invalid id")
			return
		}
		b, err := dbGetBook(db, id)
		if err == sql.ErrNoRows {
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

func handleUpdateBook(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(r)
		if !ok {
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
		if err := dbUpdateBook(db, id, &b); err == sql.ErrNoRows {
			writeError(w, http.StatusNotFound, "book not found")
			return
		} else if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to update book")
			return
		}
		writeJSON(w, http.StatusOK, b)
	}
}

func handleDeleteBook(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(r)
		if !ok {
			writeError(w, http.StatusBadRequest, "invalid id")
			return
		}
		if err := dbDeleteBook(db, id); err == sql.ErrNoRows {
			writeError(w, http.StatusNotFound, "book not found")
			return
		} else if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to delete book")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}
}
