package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

// Handler holds the repository and provides HTTP handler methods.
type Handler struct {
	Repo BookRepository
}

// NewHandler creates a new Handler with the given repository.
func NewHandler(repo BookRepository) *Handler {
	return &Handler{Repo: repo}
}

// healthCheck handles GET /health
func (h *Handler) healthCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// createBook handles POST /books
func (h *Handler) createBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	// Validation: title and author are required
	if strings.TrimSpace(req.Title) == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "title is required"})
		return
	}
	if strings.TrimSpace(req.Author) == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "author is required"})
		return
	}

	book, err := h.Repo.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "failed to create book"})
		return
	}

	writeJSON(w, http.StatusCreated, book)
}

// listBooks handles GET /books
func (h *Handler) listBooks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	authorFilter := r.URL.Query().Get("author")
	var authorPtr *string
	if authorFilter != "" {
		authorPtr = &authorFilter
	}

	books, err := h.Repo.ListBooks(authorPtr)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "failed to list books"})
		return
	}

	if books == nil {
		books = []Book{}
	}

	writeJSON(w, http.StatusOK, books)
}

// getBook handles GET /books/{id}
func (h *Handler) getBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid book ID"})
		return
	}

	book, err := h.Repo.GetBook(id)
	if err != nil {
		if err == ErrNotFound {
			writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "book not found"})
			return
		}
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// updateBook handles PUT /books/{id}
func (h *Handler) updateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid book ID"})
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	book, err := h.Repo.UpdateBook(id, req)
	if err != nil {
		if err == ErrNotFound {
			writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "book not found"})
			return
		}
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// deleteBook handles DELETE /books/{id}
func (h *Handler) deleteBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid book ID"})
		return
	}

	if err := h.Repo.DeleteBook(id); err != nil {
		if err == ErrNotFound {
			writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "book not found"})
			return
		}
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// writeJSON is a helper to encode and write JSON responses.
func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}
