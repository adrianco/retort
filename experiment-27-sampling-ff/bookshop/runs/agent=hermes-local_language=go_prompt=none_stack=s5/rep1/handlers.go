package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// API is the HTTP handler for all book endpoints.
type API struct {
	store *BookStore
}

// NewAPI creates a new API handler.
func NewAPI(store *BookStore) *API {
	return &API{store: store}
}

// HealthCheck responds with a simple JSON status.
func (a *API) HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// CreateBook handles POST /books.
func (a *API) CreateBook(w http.ResponseWriter, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if strings.TrimSpace(req.Title) == "" {
		http.Error(w, `{"error":"title is required"}`, http.StatusBadRequest)
		return
	}
	if strings.TrimSpace(req.Author) == "" {
		http.Error(w, `{"error":"author is required"}`, http.StatusBadRequest)
		return
	}

	book, err := a.store.Create(req)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			http.Error(w, `{"error":"isbn already exists"}`, http.StatusConflict)
			return
		}
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// ListBooks handles GET /books with optional ?author= filter.
func (a *API) ListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")

	books, err := a.store.GetAll(author)
	if err != nil {
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	if books == nil {
		books = []*Book{}
	}
	json.NewEncoder(w).Encode(books)
}

// GetBook handles GET /books/{id}.
func (a *API) GetBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, `{"error":"invalid book id"}`, http.StatusBadRequest)
		return
	}

	book, err := a.store.GetByID(id)
	if errors.Is(err, sql.ErrNoRows) {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}
	if err != nil {
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// UpdateBook handles PUT /books/{id}.
func (a *API) UpdateBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, `{"error":"invalid book id"}`, http.StatusBadRequest)
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if req.Title == nil && req.Author == nil && req.Year == nil && req.ISBN == nil {
		http.Error(w, `{"error":"at least one field must be provided"}`, http.StatusBadRequest)
		return
	}

	if req.Title != nil && strings.TrimSpace(*req.Title) == "" {
		http.Error(w, `{"error":"title cannot be empty"}`, http.StatusBadRequest)
		return
	}
	if req.Author != nil && strings.TrimSpace(*req.Author) == "" {
		http.Error(w, `{"error":"author cannot be empty"}`, http.StatusBadRequest)
		return
	}

	book, err := a.store.Update(id, req)
	if errors.Is(err, sql.ErrNoRows) {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}
	if err != nil {
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// DeleteBook handles DELETE /books/{id}.
func (a *API) DeleteBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, `{"error":"invalid book id"}`, http.StatusBadRequest)
		return
	}

	err = a.store.Delete(id)
	if errors.Is(err, sql.ErrNoRows) {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}
	if err != nil {
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
