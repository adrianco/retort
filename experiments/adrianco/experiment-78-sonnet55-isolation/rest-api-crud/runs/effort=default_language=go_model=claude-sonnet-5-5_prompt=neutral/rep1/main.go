package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
)

func main() {
	dsn := getenv("DB_PATH", "books.db")
	store, err := NewStore(dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer store.Close()
	addr := getenv("ADDR", ":8080")
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, NewServer(store)))
}

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

// NewServer builds the HTTP handler.
func NewServer(s *Store) http.Handler {
	h := &handlers{s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", h.create)
	mux.HandleFunc("GET /books", h.list)
	mux.HandleFunc("GET /books/{id}", h.get)
	mux.HandleFunc("PUT /books/{id}", h.update)
	mux.HandleFunc("DELETE /books/{id}", h.delete)
	return mux
}

type handlers struct{ s *Store }

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func serverErr(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeErr(w, http.StatusInternalServerError, "internal error")
}

// decode parses and validates a book from the request body.
func decode(w http.ResponseWriter, r *http.Request) (*Book, bool) {
	var b Book
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON body")
		return nil, false
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	switch {
	case b.Title == "":
		writeErr(w, http.StatusBadRequest, "title is required")
	case b.Author == "":
		writeErr(w, http.StatusBadRequest, "author is required")
	case b.Year < 0:
		writeErr(w, http.StatusBadRequest, "year must not be negative")
	default:
		return &b, true
	}
	return nil, false
}

func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeErr(w, http.StatusBadRequest, "invalid id")
		return 0, false
	}
	return id, true
}

func (h *handlers) create(w http.ResponseWriter, r *http.Request) {
	b, ok := decode(w, r)
	if !ok {
		return
	}
	if err := h.s.Create(b); err != nil {
		serverErr(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (h *handlers) list(w http.ResponseWriter, r *http.Request) {
	books, err := h.s.List(r.URL.Query().Get("author"))
	if err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (h *handlers) get(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := h.s.Get(id)
	if errors.Is(err, sql.ErrNoRows) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handlers) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, ok := decode(w, r)
	if !ok {
		return
	}
	b.ID = id
	if err := h.s.Update(b); errors.Is(err, sql.ErrNoRows) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (h *handlers) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := h.s.Delete(id); errors.Is(err, sql.ErrNoRows) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverErr(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
