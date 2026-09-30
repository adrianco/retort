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

func (a *API) routes() http.Handler {
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

func fail(w http.ResponseWriter, err error) {
	if errors.Is(err, ErrNotFound) {
		writeErr(w, http.StatusNotFound, "book not found")
		return
	}
	log.Println("internal error:", err)
	writeErr(w, http.StatusInternalServerError, "internal error")
}

func decode(w http.ResponseWriter, r *http.Request) (*Book, bool) {
	var b Book
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(&b); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON body")
		return nil, false
	}
	b.Title, b.Author = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author)
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
	if err != nil {
		writeErr(w, http.StatusBadRequest, "invalid id")
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
		fail(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, b)
}

func (a *API) list(w http.ResponseWriter, r *http.Request) {
	books, err := a.store.List(r.URL.Query().Get("author"))
	if err != nil {
		fail(w, err)
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
		fail(w, err)
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
		fail(w, err)
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
		fail(w, err)
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
	log.Println("listening on", addr)
	log.Fatal(http.ListenAndServe(addr, (&API{store}).routes()))
}
