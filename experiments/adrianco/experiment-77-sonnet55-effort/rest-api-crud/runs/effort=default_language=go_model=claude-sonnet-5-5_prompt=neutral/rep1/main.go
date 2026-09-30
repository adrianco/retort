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

func serverErr(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeErr(w, http.StatusInternalServerError, "internal server error")
}

// decodeBook parses and validates a request body.
func decodeBook(r *http.Request) (Book, string) {
	var b Book
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	if err := dec.Decode(&b); err != nil {
		return b, "invalid JSON body"
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	switch {
	case b.Title == "":
		return b, "title is required"
	case b.Author == "":
		return b, "author is required"
	case b.Year < 0:
		return b, "year must not be negative"
	}
	return b, ""
}

func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeErr(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unhealthy"})
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
	if err := s.store.Create(&b); err != nil {
		serverErr(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (s *server) list(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.URL.Query().Get("author"))
	if err != nil {
		serverErr(w, err)
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
	if errors.Is(err, errNotFound) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, msg := decodeBook(r)
	if msg != "" {
		writeErr(w, http.StatusBadRequest, msg)
		return
	}
	b.ID = id
	if err := s.store.Update(&b); errors.Is(err, errNotFound) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (s *server) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(id); errors.Is(err, errNotFound) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	} else if err != nil {
		serverErr(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func main() {
	dbPath := getenv("DB_PATH", "books.db")
	addr := getenv("ADDR", ":8080")
	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()
	log.Printf("listening on %s (db %s)", addr, dbPath)
	log.Fatal(http.ListenAndServe(addr, newHandler(store)))
}

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
