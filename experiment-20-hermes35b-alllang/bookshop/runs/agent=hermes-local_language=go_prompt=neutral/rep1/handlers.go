package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/gorilla/mux"
)

// Handler holds dependencies for HTTP handlers.
type Handler struct {
	DB *Database
}

// writeJSON writes a value as a JSON response with the given status code.
func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

// writeError writes an error JSON response with the given status code.
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, ErrorResponse{Error: message})
}

// HealthCheck handles GET /health.
func (h *Handler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// CreateBook handles POST /books.
func (h *Handler) CreateBook(w http.ResponseWriter, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON payload")
		return
	}

	// Validation: title and author are required
	if strings.TrimSpace(req.Title) == "" {
		writeError(w, http.StatusBadRequest, "Title is required")
		return
	}
	if strings.TrimSpace(req.Author) == "" {
		writeError(w, http.StatusBadRequest, "Author is required")
		return
	}

	book, err := h.DB.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to create book")
		return
	}

	writeJSON(w, http.StatusCreated, book)
}

// ListBooks handles GET /books.
func (h *Handler) ListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	var authorFilter *string
	if author != "" {
		authorFilter = &author
	}

	books, err := h.DB.ListBooks(authorFilter)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to list books")
		return
	}

	writeJSON(w, http.StatusOK, books)
}

// GetBook handles GET /books/{id}.
func (h *Handler) GetBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.ParseInt(vars["id"], 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	book, err := h.DB.GetBookByID(id)
	if err != nil {
		writeError(w, http.StatusNotFound, "Book not found")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// UpdateBook handles PUT /books/{id}.
func (h *Handler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.ParseInt(vars["id"], 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON payload")
		return
	}

	// Validation: if title is provided, it must not be empty
	if req.Title != nil && strings.TrimSpace(*req.Title) == "" {
		writeError(w, http.StatusBadRequest, "Title is required")
		return
	}
	// Validation: if author is provided, it must not be empty
	if req.Author != nil && strings.TrimSpace(*req.Author) == "" {
		writeError(w, http.StatusBadRequest, "Author is required")
		return
	}

	book, err := h.DB.UpdateBook(id, &req)
	if err != nil {
		writeError(w, http.StatusNotFound, "Book not found")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// DeleteBook handles DELETE /books/{id}.
func (h *Handler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.ParseInt(vars["id"], 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	deleted, err := h.DB.DeleteBook(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to delete book")
		return
	}

	if !deleted {
		writeError(w, http.StatusNotFound, "Book not found")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
