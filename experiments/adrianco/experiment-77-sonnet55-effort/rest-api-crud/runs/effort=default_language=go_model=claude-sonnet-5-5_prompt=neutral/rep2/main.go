package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
)

type server struct{ store *Store }

// newHandler builds the HTTP router for the API.
func newHandler(s *Store) http.Handler {
	srv := &server{store: s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", srv.health)
	mux.HandleFunc("POST /books", srv.create)
	mux.HandleFunc("GET /books", srv.list)
	mux.HandleFunc("GET /books/{id}", srv.get)
	mux.HandleFunc("PUT /books/{id}", srv.update)
	mux.HandleFunc("DELETE /books/{id}", srv.delete)
	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (s *server) fail(w http.ResponseWriter, err error) {
	if errors.Is(err, errNotFound) {
		writeErr(w, http.StatusNotFound, err.Error())
		return
	}
	log.Printf("internal error: %v", err)
	writeErr(w, http.StatusInternalServerError, "internal server error")
}

func pathID(r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	return id, err == nil && id > 0
}

// decodeBook parses and validates a request body.
func decodeBook(r *http.Request) (*Book, string) {
	var b Book
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	if err := dec.Decode(&b); err != nil {
		return nil, "invalid JSON body"
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	switch {
	case b.Title == "":
		return nil, "title is required"
	case b.Author == "":
		return nil, "author is required"
	case b.Year < 0:
		return nil, "year must not be negative"
	}
	return &b, ""
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(); err != nil {
		writeErr(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) create(w http.ResponseWriter, r *http.Request) {
	b, msg := decodeBook(r)
	if msg != "" {
		writeErr(w, http.StatusBadRequest, msg)
		return
	}
	b.ID = 0
	if err := s.store.Create(b); err != nil {
		s.fail(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *server) list(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.URL.Query().Get("author"))
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) get(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeErr(w, http.StatusBadRequest, "invalid id")
		return
	}
	b, err := s.store.Get(id)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeErr(w, http.StatusBadRequest, "invalid id")
		return
	}
	b, msg := decodeBook(r)
	if msg != "" {
		writeErr(w, http.StatusBadRequest, msg)
		return
	}
	b.ID = id
	if err := s.store.Update(b); err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(r)
	if !ok {
		writeErr(w, http.StatusBadRequest, "invalid id")
		return
	}
	if err := s.store.Delete(id); err != nil {
		s.fail(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func main() {
	store, err := NewStore(getenv("DB_PATH", "books.db"))
	if err != nil {
		log.Fatal(err)
	}
	defer store.Close()
	addr := getenv("ADDR", ":8080")
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, newHandler(store)))
}
