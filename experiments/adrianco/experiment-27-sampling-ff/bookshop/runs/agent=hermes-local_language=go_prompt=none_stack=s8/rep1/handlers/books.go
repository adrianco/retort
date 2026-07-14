package handlers

import (
	"book-api/db"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/gorilla/mux"
)

// BooksHandler handles HTTP requests for book operations.
type BooksHandler struct {
	Db *db.Database
}

// NewBooksHandler creates a new handler instance.
func NewBooksHandler(database *db.Database) *BooksHandler {
	return &BooksHandler{Db: database}
}

// HealthCheck handles the /health endpoint.
func (h *BooksHandler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "healthy",
	})
}

// CreateBook handles POST /books.
func (h *BooksHandler) CreateBook(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if req.Title == "" {
		http.Error(w, `{"error":"title is required"}`, http.StatusBadRequest)
		return
	}
	if req.Author == "" {
		http.Error(w, `{"error":"author is required"}`, http.StatusBadRequest)
		return
	}

	book, err := h.Db.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		http.Error(w, `{"error":"failed to create book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// GetBooks handles GET /books and GET /books?author=...
func (h *BooksHandler) GetBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	books, err := h.Db.GetAllBooks(authorFilter)
	if err != nil {
		http.Error(w, `{"error":"failed to retrieve books"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

// GetBook handles GET /books/{id}.
func (h *BooksHandler) GetBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	idStr := vars["id"]

	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error":"invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := h.Db.GetBookByID(id)
	if err != nil {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// UpdateBook handles PUT /books/{id}.
func (h *BooksHandler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	idStr := vars["id"]

	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error":"invalid book ID"}`, http.StatusBadRequest)
		return
	}

	var req map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if title, ok := req["title"].(string); ok {
		if strings.TrimSpace(title) == "" {
			http.Error(w, `{"error":"title cannot be empty"}`, http.StatusBadRequest)
			return
		}
	}
	if author, ok := req["author"].(string); ok {
		if strings.TrimSpace(author) == "" {
			http.Error(w, `{"error":"author cannot be empty"}`, http.StatusBadRequest)
			return
		}
	}

	var title *string
	if v, ok := req["title"].(string); ok {
		title = &v
	}
	var author *string
	if v, ok := req["author"].(string); ok {
		author = &v
	}
	var year *int
	if v, ok := req["year"].(float64); ok {
		vInt := int(v)
		year = &vInt
	}
	var isbn *string
	if v, ok := req["isbn"].(string); ok {
		isbn = &v
	}

	book, err := h.Db.UpdateBook(id, title, author, year, isbn)
	if err != nil {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// DeleteBook handles DELETE /books/{id}.
func (h *BooksHandler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	idStr := vars["id"]

	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error":"invalid book ID"}`, http.StatusBadRequest)
		return
	}

	if err := h.Db.DeleteBook(id); err != nil {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
