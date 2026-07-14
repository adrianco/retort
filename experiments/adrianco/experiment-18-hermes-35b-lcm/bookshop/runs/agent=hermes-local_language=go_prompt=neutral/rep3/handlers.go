package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

// Handlers holds the database and provides HTTP handler methods.
type Handlers struct {
	DB *DB
}

// newJSONHandler wraps a handler function with JSON write helpers.
func newJSONHandler(fn func(w http.ResponseWriter, r *http.Request) (int, interface{})) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		status, body := fn(w, r)
		w.WriteHeader(status)
		if body != nil {
			json.NewEncoder(w).Encode(body)
		}
	}
}

// healthHandler returns 200 OK for health checks.
func (h *Handlers) healthHandler(w http.ResponseWriter, r *http.Request) (int, interface{}) {
	if err := h.DB.HealthCheck(); err != nil {
		return http.StatusServiceUnavailable, ErrorResponse{Error: "database unhealthy"}
	}
	return http.StatusOK, map[string]string{"status": "ok"}
}

// createBookHandler validates input and creates a new book.
func (h *Handlers) createBookHandler(w http.ResponseWriter, r *http.Request) (int, interface{}) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"}
	}

	// Validate required fields
	var validations []ValidationError
	if strings.TrimSpace(req.Title) == "" {
		validations = append(validations, ValidationError{Field: "title", Message: "title is required"})
	}
	if strings.TrimSpace(req.Author) == "" {
		validations = append(validations, ValidationError{Field: "author", Message: "author is required"})
	}
	if len(validations) > 0 {
		return http.StatusBadRequest, ErrorResponse{Error: "validation failed", Validations: validations}
	}

	book, err := h.DB.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		return http.StatusInternalServerError, ErrorResponse{Error: "failed to create book"}
	}

	return http.StatusCreated, SuccessResponse{Message: "book created", Book: *book}
}

// listBooksHandler returns all books, optionally filtered by author.
func (h *Handlers) listBooksHandler(w http.ResponseWriter, r *http.Request) (int, interface{}) {
	authorFilter := r.URL.Query().Get("author")
	var filter *string
	if authorFilter != "" {
		filter = &authorFilter
	}

	books, err := h.DB.ListBooks(filter)
	if err != nil {
		return http.StatusInternalServerError, ErrorResponse{Error: "failed to list books"}
	}

	if books == nil {
		books = []Book{}
	}

	return http.StatusOK, books
}

// getBookHandler returns a single book by ID.
func (h *Handlers) getBookHandler(w http.ResponseWriter, r *http.Request) (int, interface{}) {
	id, err := parseIDFromPath(r.URL.Path)
	if err != nil {
		return http.StatusBadRequest, ErrorResponse{Error: "invalid book ID"}
	}

	book, err := h.DB.GetBook(id)
	if err != nil {
		return http.StatusInternalServerError, ErrorResponse{Error: "failed to get book"}
	}
	if book == nil {
		return http.StatusNotFound, ErrorResponse{Error: "book not found"}
	}

	return http.StatusOK, book
}

// updateBookHandler updates an existing book with provided fields.
func (h *Handlers) updateBookHandler(w http.ResponseWriter, r *http.Request) (int, interface{}) {
	id, err := parseIDFromPath(r.URL.Path)
	if err != nil {
		return http.StatusBadRequest, ErrorResponse{Error: "invalid book ID"}
	}

	// Check existence first
	existing, err := h.DB.GetBook(id)
	if err != nil {
		return http.StatusInternalServerError, ErrorResponse{Error: "failed to get book"}
	}
	if existing == nil {
		return http.StatusNotFound, ErrorResponse{Error: "book not found"}
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"}
	}

	// At least one field must be non-nil
	if req.Title == nil && req.Author == nil && req.Year == nil && req.ISBN == nil {
		return http.StatusBadRequest, ErrorResponse{Error: "at least one field must be provided"}
	}

	book, err := h.DB.UpdateBook(id, &req)
	if err != nil {
		return http.StatusInternalServerError, ErrorResponse{Error: "failed to update book"}
	}

	return http.StatusOK, book
}

// deleteBookHandler deletes a book by ID.
func (h *Handlers) deleteBookHandler(w http.ResponseWriter, r *http.Request) (int, interface{}) {
	id, err := parseIDFromPath(r.URL.Path)
	if err != nil {
		return http.StatusBadRequest, ErrorResponse{Error: "invalid book ID"}
	}

	book, err := h.DB.GetBook(id)
	if err != nil {
		return http.StatusInternalServerError, ErrorResponse{Error: "failed to get book"}
	}
	if book == nil {
		return http.StatusNotFound, ErrorResponse{Error: "book not found"}
	}

	if err := h.DB.DeleteBook(id); err != nil {
		return http.StatusInternalServerError, ErrorResponse{Error: "failed to delete book"}
	}

	return http.StatusOK, map[string]string{"message": "book deleted"}
}

// parseIDFromPath extracts the integer ID from a URL path like /books/123.
func parseIDFromPath(path string) (int64, error) {
	parts := strings.Split(strings.TrimSpace(path), "/")
	// Expected: ["", "books", "123"]
	if len(parts) < 3 {
		return 0, strconv.ErrSyntax
	}
	return strconv.ParseInt(parts[len(parts)-1], 10, 64)
}
