package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// BookHandler handles HTTP requests for the books API.
type BookHandler struct {
	Store *BookStore
}

// NewBookHandler creates a new BookHandler.
func NewBookHandler(store *BookStore) *BookHandler {
	return &BookHandler{Store: store}
}

// Health handles the /health endpoint.
func (h *BookHandler) Health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok",
	})
}

// HandleBooks handles GET /books (list) and POST /books (create).
func (h *BookHandler) HandleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.listBooks(w, r)
	case http.MethodPost:
		h.createBook(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// HandleBookByID handles GET/PUT/DELETE /books/{id}.
func (h *BookHandler) HandleBookByID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodPut && r.Method != http.MethodDelete {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	// Extract ID from URL path: /books/{id}
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/books/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		writeError(w, http.StatusBadRequest, "book ID is required")
		return
	}

	id, err := strconv.Atoi(parts[0])
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	switch r.Method {
	case http.MethodGet:
		h.getBook(w, id)
	case http.MethodPut:
		h.updateBook(w, id, r)
	case http.MethodDelete:
		h.deleteBook(w, id)
	}
}

// listBooks handles GET /books?author=...
func (h *BookHandler) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")

	books, err := h.Store.GetAllBooks(author)
	if err != nil {
		log.Printf("Error listing books: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}

	if books == nil {
		books = []Book{}
	}

	writeJSON(w, http.StatusOK, books)
}

// createBook handles POST /books
func (h *BookHandler) createBook(w http.ResponseWriter, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	// Validate required fields
	var validationErrors []ValidationError
	if req.Title == "" {
		validationErrors = append(validationErrors, ValidationError{Field: "title", Message: "title is required"})
	}
	if req.Author == "" {
		validationErrors = append(validationErrors, ValidationError{Field: "author", Message: "author is required"})
	}

	if len(validationErrors) > 0 {
		writeJSON(w, http.StatusBadRequest, ValidationErrorsBody{Errors: validationErrors})
		return
	}

	book, err := h.Store.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		log.Printf("Error creating book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}

	writeJSON(w, http.StatusCreated, book)
}

// getBook handles GET /books/{id}
func (h *BookHandler) getBook(w http.ResponseWriter, id int) {
	book, err := h.Store.GetBookByID(id)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		log.Printf("Error getting book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// updateBook handles PUT /books/{id}
func (h *BookHandler) updateBook(w http.ResponseWriter, id int, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	// Validate required fields
	var validationErrors []ValidationError
	if req.Title == "" {
		validationErrors = append(validationErrors, ValidationError{Field: "title", Message: "title is required"})
	}
	if req.Author == "" {
		validationErrors = append(validationErrors, ValidationError{Field: "author", Message: "author is required"})
	}

	if len(validationErrors) > 0 {
		writeJSON(w, http.StatusBadRequest, ValidationErrorsBody{Errors: validationErrors})
		return
	}

	book, err := h.Store.UpdateBook(id, req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		log.Printf("Error updating book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// deleteBook handles DELETE /books/{id}
func (h *BookHandler) deleteBook(w http.ResponseWriter, id int) {
	err := h.Store.DeleteBook(id)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "book not found")
			return
		}
		log.Printf("Error deleting book: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
