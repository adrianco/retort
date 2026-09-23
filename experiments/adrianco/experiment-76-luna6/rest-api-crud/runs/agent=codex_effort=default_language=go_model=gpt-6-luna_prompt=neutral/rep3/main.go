package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
)

type API struct{ db *sql.DB }

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" {
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", http.MethodGet)
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		if err := a.db.Ping(); err != nil {
			writeError(w, http.StatusServiceUnavailable, "database unavailable")
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}
	if r.URL.Path == "/books" {
		a.collection(w, r)
		return
	}
	if strings.HasPrefix(r.URL.Path, "/books/") {
		a.item(w, r)
		return
	}
	writeError(w, http.StatusNotFound, "not found")
}

func (a *API) collection(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		b, ok := decodeBook(w, r)
		if !ok {
			return
		}
		created, err := createBook(a.db, b)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create book")
			return
		}
		writeJSON(w, http.StatusCreated, created)
	case http.MethodGet:
		books, err := listBooks(a.db, r.URL.Query().Get("author"))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not list books")
			return
		}
		writeJSON(w, http.StatusOK, books)
	default:
		methodNotAllowed(w, "GET, POST")
	}
}

func (a *API) item(w http.ResponseWriter, r *http.Request) {
	rawID := strings.TrimPrefix(r.URL.Path, "/books/")
	if rawID == "" || strings.Contains(rawID, "/") {
		writeError(w, http.StatusNotFound, "not found")
		return
	}
	id, err := strconv.ParseInt(rawID, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return
	}
	switch r.Method {
	case http.MethodGet:
		b, err := getBook(a.db, id)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
		} else if err != nil {
			writeError(w, http.StatusInternalServerError, "could not get book")
		} else {
			writeJSON(w, http.StatusOK, b)
		}
	case http.MethodPut:
		b, ok := decodeBook(w, r)
		if !ok {
			return
		}
		updated, err := updateBook(a.db, id, b)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
		} else if err != nil {
			writeError(w, http.StatusInternalServerError, "could not update book")
		} else {
			writeJSON(w, http.StatusOK, updated)
		}
	case http.MethodDelete:
		if err := deleteBook(a.db, id); errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
		} else if err != nil {
			writeError(w, http.StatusInternalServerError, "could not delete book")
		} else {
			w.WriteHeader(http.StatusNoContent)
		}
	default:
		methodNotAllowed(w, "GET, PUT, DELETE")
	}
}

func decodeBook(w http.ResponseWriter, r *http.Request) (Book, bool) {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var b Book
	if err := dec.Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return Book{}, false
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		writeError(w, http.StatusBadRequest, "request must contain one JSON object")
		return Book{}, false
	}
	b.Title, b.Author = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return Book{}, false
	}
	b.ID = 0
	return b, true
}

func methodNotAllowed(w http.ResponseWriter, allow string) {
	w.Header().Set("Allow", allow)
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func main() {
	dsn := os.Getenv("BOOKS_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	db, err := openDatabase(dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("book API listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, &API{db: db}))
}
