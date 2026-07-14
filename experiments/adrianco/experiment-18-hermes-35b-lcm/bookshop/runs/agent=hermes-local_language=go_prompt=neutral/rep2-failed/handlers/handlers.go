package handlers

import (
	"encoding/json"
	"net/http"
	"strings"

	"book-api/models"
)

// BookHandler handles HTTP requests for books.
type BookHandler struct {
	store models.BookStore
}

// NewBookHandler creates a new BookHandler.
func NewBookHandler(store models.BookStore) *BookHandler {
	return &BookHandler{store: store}
}

// HealthCheck returns a simple health check response.
func (h *BookHandler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// CreateBook handles POST /books
func (h *BookHandler) CreateBook(w http.ResponseWriter, r *http.Request) {
	var req models.CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if err := req.Validate(); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	book := &models.Book{
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	if err := h.store.Create(book); err != nil {
		http.Error(w, `{"error": "failed to create book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// ListBooks handles GET /books
func (h *BookHandler) ListBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	books, err := h.store.List(authorFilter)
	if err != nil {
		http.Error(w, `{"error": "failed to list books"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(books)
}

// GetBook handles GET /books/{id}
func (h *BookHandler) GetBook(w http.ResponseWriter, r *http.Request) {
	id := extractIDFromURL(r.URL.Path)
	if id == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "book ID is required"})
		return
	}

	book, err := h.store.GetByID(id)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

// UpdateBook handles PUT /books/{id}
func (h *BookHandler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	id := extractIDFromURL(r.URL.Path)
	if id == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "book ID is required"})
		return
	}

	var req models.UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "invalid JSON"}`, http.StatusBadRequest)
		return
	}

	book, err := h.store.Update(id, req)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		if err.Error() == "title cannot be empty" ||
			err.Error() == "author cannot be empty" ||
			err.Error() == "year must be a positive integer" {
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
			return
		}
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

// DeleteBook handles DELETE /books/{id}
func (h *BookHandler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	id := extractIDFromURL(r.URL.Path)
	if id == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "book ID is required"})
		return
	}

	err := h.store.Delete(id)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"message": "book deleted successfully"})
}

// RegisterRoutes sets up the book routes on the ServeMux.
func RegisterRoutes(mux *http.ServeMux, h *BookHandler) {
	mux.HandleFunc("/books", h.handleBooks)
	mux.HandleFunc("/books/", h.handleBookByID)
	mux.HandleFunc("/health", h.HealthCheck)
}

// handleBooks dispatches to the right handler based on method.
// Used for: GET /books (list), POST /books (create)
func (h *BookHandler) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.ListBooks(w, r)
	case http.MethodPost:
		h.CreateBook(w, r)
	default:
		http.Error(w, `{"error": "method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

// handleBookByID dispatches to the right handler based on method.
// Used for: GET /books/{id}, PUT /books/{id}, DELETE /books/{id}
func (h *BookHandler) handleBookByID(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.GetBook(w, r)
	case http.MethodPut:
		h.UpdateBook(w, r)
	case http.MethodDelete:
		h.DeleteBook(w, r)
	default:
		http.Error(w, `{"error": "method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

// extractIDFromURL extracts the ID from /books/123 path segment.
func extractIDFromURL(path string) string {
	// path like /books/ or /books/123
	path = strings.TrimRight(path, "/")
	parts := strings.Split(path, "/")
	if len(parts) < 3 {
		// e.g. "/books" only, no ID
		return ""
	}
	id := parts[len(parts)-1]
	if id == "" {
		return ""
	}
	return id
}
