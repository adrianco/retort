package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"
)

func newHandler(db *sql.DB) http.Handler {
	h := &apiHandler{store: bookStore{db: db}}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("/books", h.books)
	mux.HandleFunc("/books/{id}", h.book)
	return mux
}

type apiHandler struct{ store bookStore }

func (h *apiHandler) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *apiHandler) books(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		books, err := h.store.list(strings.TrimSpace(r.URL.Query().Get("author")))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		writeJSON(w, http.StatusOK, books)
	case http.MethodPost:
		var b Book
		if err := decodeBook(w, r, &b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		if err := validateBook(b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		created, err := h.store.create(b)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		writeJSON(w, http.StatusCreated, created)
	default:
		methodNotAllowed(w)
	}
}

func (h *apiHandler) book(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "book id must be a positive integer")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := h.store.get(id)
		if err != nil {
			writeStoreError(w, err, "could not get book")
			return
		}
		writeJSON(w, http.StatusOK, b)
	case http.MethodPut:
		var b Book
		if err := decodeBook(w, r, &b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		if err := validateBook(b); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		updated, err := h.store.update(id, b)
		if err != nil {
			writeStoreError(w, err, "could not update book")
			return
		}
		writeJSON(w, http.StatusOK, updated)
	case http.MethodDelete:
		if err := h.store.delete(id); err != nil {
			writeStoreError(w, err, "could not delete book")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		methodNotAllowed(w)
	}
}

func decodeBook(w http.ResponseWriter, r *http.Request, b *Book) error {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(b); err != nil {
		return errors.New("request body must be a valid book JSON object")
	}
	var extra any
	if err := dec.Decode(&extra); !errors.Is(err, io.EOF) {
		return errors.New("request body must contain exactly one JSON object")
	}
	return nil
}

func writeStoreError(w http.ResponseWriter, err error, message string) {
	if errors.Is(err, errNotFound) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	writeError(w, http.StatusInternalServerError, message)
}

func methodNotAllowed(w http.ResponseWriter) {
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
