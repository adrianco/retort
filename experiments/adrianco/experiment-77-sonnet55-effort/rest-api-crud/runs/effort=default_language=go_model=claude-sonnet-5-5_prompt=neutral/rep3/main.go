package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
)

type server struct{ store *Store }

func newHandler(s *Store) http.Handler {
	srv := &server{store: s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
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

func (s *server) serverErr(w http.ResponseWriter, err error) {
	if errors.Is(err, errNotFound) {
		writeErr(w, http.StatusNotFound, err.Error())
		return
	}
	log.Printf("internal error: %v", err)
	writeErr(w, http.StatusInternalServerError, "internal server error")
}

// decodeBook parses and validates a request body.
func decodeBook(w http.ResponseWriter, r *http.Request) (*Book, bool) {
	var b Book
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON body")
		return nil, false
	}
	b.Title, b.Author, b.ISBN = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), strings.TrimSpace(b.ISBN)
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
		writeErr(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func (s *server) create(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	if err := s.store.Create(b); err != nil {
		s.serverErr(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *server) list(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.URL.Query().Get("author"))
	if err != nil {
		s.serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) get(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := s.store.Get(id)
	if err != nil {
		s.serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	b.ID = id
	if err := s.store.Update(b); err != nil {
		s.serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(id); err != nil {
		s.serverErr(w, err)
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
