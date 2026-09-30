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

type API struct{ store *Store }

func NewHandler(s *Store) http.Handler {
	a := &API{s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", a.create)
	mux.HandleFunc("GET /books", a.list)
	mux.HandleFunc("GET /books/{id}", a.get)
	mux.HandleFunc("PUT /books/{id}", a.update)
	mux.HandleFunc("DELETE /books/{id}", a.delete)
	return mux
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func serverErr(w http.ResponseWriter, err error) {
	if errors.Is(err, errNotFound) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	}
	log.Printf("internal error: %v", err)
	writeErr(w, http.StatusInternalServerError, "internal server error")
}

// decode parses and validates a book payload; it writes the error response on failure.
func decode(w http.ResponseWriter, r *http.Request) (*Book, bool) {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	var b Book
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

func (a *API) create(w http.ResponseWriter, r *http.Request) {
	b, ok := decode(w, r)
	if !ok {
		return
	}
	if err := a.store.Create(b); err != nil {
		serverErr(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(b.ID, 10))
	writeJSON(w, http.StatusCreated, b)
}

func (a *API) list(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.URL.Query().Get("author"))
	if err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *API) get(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, err := a.store.Get(id)
	if err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, ok := decode(w, r)
	if !ok {
		return
	}
	b.ID = id
	if err := a.store.Update(b); err != nil {
		serverErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *API) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	if err := a.store.Delete(id); err != nil {
		serverErr(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func main() {
	dsn := os.Getenv("DB_PATH")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	store, err := NewStore(dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer store.Close()
	log.Printf("listening on %s (db: %s)", addr, dsn)
	log.Fatal(http.ListenAndServe(addr, NewHandler(store)))
}
