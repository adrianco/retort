package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func (in *bookInput) validate() map[string]string {
	errs := map[string]string{}
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
	if in.Title == "" {
		errs["title"] = "title is required"
	}
	if in.Author == "" {
		errs["author"] = "author is required"
	}
	if in.Year < 0 || in.Year > 9999 {
		errs["year"] = "year must be between 0 and 9999"
	}
	return errs
}

func NewServer(s *Store) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := s.Ping(); err != nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", func(w http.ResponseWriter, r *http.Request) {
		in, ok := decodeInput(w, r)
		if !ok {
			return
		}
		b := Book{Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
		if err := s.Create(&b); err != nil {
			writeError(w, http.StatusInternalServerError, "internal error")
			return
		}
		writeJSON(w, http.StatusCreated, b)
	})
	mux.HandleFunc("GET /books", func(w http.ResponseWriter, r *http.Request) {
		books, err := s.List(r.URL.Query().Get("author"))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "internal error")
			return
		}
		writeJSON(w, http.StatusOK, books)
	})
	mux.HandleFunc("GET /books/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(w, r)
		if !ok {
			return
		}
		b, err := s.Get(id)
		if !handleErr(w, err) {
			return
		}
		writeJSON(w, http.StatusOK, b)
	})
	mux.HandleFunc("PUT /books/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(w, r)
		if !ok {
			return
		}
		in, ok := decodeInput(w, r)
		if !ok {
			return
		}
		b := Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
		if !handleErr(w, s.Update(&b)) {
			return
		}
		writeJSON(w, http.StatusOK, b)
	})
	mux.HandleFunc("DELETE /books/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(w, r)
		if !ok {
			return
		}
		if !handleErr(w, s.Delete(id)) {
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	return mux
}

func decodeInput(w http.ResponseWriter, r *http.Request) (*bookInput, bool) {
	var in bookInput
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return nil, false
	}
	if errs := in.validate(); len(errs) > 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "validation failed", "fields": errs})
		return nil, false
	}
	return &in, true
}

func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid id")
		return 0, false
	}
	return id, true
}

func handleErr(w http.ResponseWriter, err error) bool {
	switch {
	case err == nil:
		return true
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found")
	default:
		writeError(w, http.StatusInternalServerError, "internal error")
	}
	return false
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
