package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// Book represents a book in the collection
type Book struct {
	ID        uint      `gorm:"primaryKey" json:"id"`
	Title     string    `gorm:"not null" json:"title"`
	Author    string    `gorm:"not null" json:"author"`
	Year      int       `gorm:"not null" json:"year"`
	ISBN      string    `gorm:"unique;not null" json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput represents the input for creating/updating a book
type BookInput struct {
	Title string `json:"title" binding:"required"`
	Author string `json:"author" binding:"required"`
	Year  int    `json:"year" binding:"required"`
	ISBN  string `json:"isbn" binding:"required"`
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error string `json:"error"`
}

// BookResponse represents a single book response
type BookResponse struct {
	ID        uint      `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BooksResponse represents a list of books response
type BooksResponse struct {
	Books []BookResponse `json:"books"`
	Total int            `json:"total"`
}

// Handler holds the database reference and handlers
type Handler struct {
	db *gorm.DB
}

// NewHandler creates a new Handler
func NewHandler(db *gorm.DB) *Handler {
	return &Handler{db: db}
}

// InitDB initializes the database
func InitDB(dsn string) (*gorm.DB, error) {
	db, err := gorm.Open(sqlite.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	return db, nil
}

// toBookResponse converts a Book to BookResponse
func toBookResponse(book Book) BookResponse {
	return BookResponse{
		ID:        book.ID,
		Title:     book.Title,
		Author:    book.Author,
		Year:      book.Year,
		ISBN:      book.ISBN,
		CreatedAt: book.CreatedAt,
		UpdatedAt: book.UpdatedAt,
	}
}

// toBooksResponse converts a list of Books to BooksResponse
func toBooksResponse(books []Book) BooksResponse {
	responses := make([]BookResponse, len(books))
	for i, book := range books {
		responses[i] = toBookResponse(book)
	}
	return BooksResponse{
		Books: responses,
		Total: len(books),
	}
}

// handleHealth handles the /health endpoint
func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// handleBooks handles the /books endpoint (GET all, POST create)
func (h *Handler) handleBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	switch r.Method {
	case http.MethodGet:
		h.listBooks(w, r)
	case http.MethodPost:
		h.createBook(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Method not allowed"})
	}
}

// handleBookByID handles the /books/{id} endpoint
func (h *Handler) handleBookByID(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Extract ID from path
	path := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(path)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Invalid book ID"})
		return
	}

	switch r.Method {
	case http.MethodGet:
		h.getBook(w, r, id)
	case http.MethodPut:
		h.updateBook(w, r, id)
	case http.MethodDelete:
		h.deleteBook(w, r, id)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Method not allowed"})
	}
}

// listBooks handles GET /books with optional ?author= filter
func (h *Handler) listBooks(w http.ResponseWriter, r *http.Request) {
	query := h.db.Model(&Book{})

	// Check for author filter
	author := r.URL.Query().Get("author")
	if author != "" {
		query = query.Where("author = ?", author)
	}

	var books []Book
	if err := query.Find(&books).Error; err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Failed to list books"})
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(toBooksResponse(books))
}

// createBook handles POST /books
func (h *Handler) createBook(w http.ResponseWriter, r *http.Request) {
	var input BookInput

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Invalid request body"})
		return
	}

	// Validation
	if input.Title == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Title is required"})
		return
	}

	if input.Author == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Author is required"})
		return
	}

	if input.Year <= 0 {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Year must be valid"})
		return
	}

	if input.ISBN == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "ISBN is required"})
		return
	}

	book := Book{
		Title: input.Title,
		Author: input.Author,
		Year: input.Year,
		ISBN: input.ISBN,
	}

	if err := h.db.Create(&book).Error; err != nil {
		if strings.Contains(err.Error(), "UNIQUE constraint failed") {
			w.WriteHeader(http.StatusConflict)
			json.NewEncoder(w).Encode(ErrorResponse{Error: "ISBN already exists"})
			return
		}
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Failed to create book"})
		return
	}

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(toBookResponse(book))
}

// getBook handles GET /books/{id}
func (h *Handler) getBook(w http.ResponseWriter, r *http.Request, id int) {
	var book Book
	if err := h.db.First(&book, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(ErrorResponse{Error: "Book not found"})
			return
		}
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Failed to get book"})
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(toBookResponse(book))
}

// updateBook handles PUT /books/{id}
func (h *Handler) updateBook(w http.ResponseWriter, r *http.Request, id int) {
	var input BookInput

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Invalid request body"})
		return
	}

	// Validation
	if input.Title == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Title is required"})
		return
	}

	if input.Author == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Author is required"})
		return
	}

	if input.Year <= 0 {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Year must be valid"})
		return
	}

	if input.ISBN == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "ISBN is required"})
		return
	}

	// Check if book exists
	var existing Book
	if err := h.db.First(&existing, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(ErrorResponse{Error: "Book not found"})
			return
		}
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Failed to get book"})
		return
	}

	// Check if ISBN is being changed and conflicts with another book
	if existing.ISBN != input.ISBN {
		var count int64
		h.db.Model(&Book{}).Where("isbn = ?", input.ISBN).Not("id = ?", id).Count(&count)
		if count > 0 {
			w.WriteHeader(http.StatusConflict)
			json.NewEncoder(w).Encode(ErrorResponse{Error: "ISBN already exists"})
			return
		}
	}

	// Update the book
	book := Book{
		ID:        uint(id),
		Title:     input.Title,
		Author:    input.Author,
		Year:      input.Year,
		ISBN:      input.ISBN,
	}

	if err := h.db.Model(&existing).Updates(book).Error; err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Failed to update book"})
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(toBookResponse(book))
}

// deleteBook handles DELETE /books/{id}
func (h *Handler) deleteBook(w http.ResponseWriter, r *http.Request, id int) {
	// Check if book exists
	var book Book
	if err := h.db.First(&book, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(ErrorResponse{Error: "Book not found"})
			return
		}
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Failed to get book"})
		return
	}

	if err := h.db.Delete(&book).Error; err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{Error: "Failed to delete book"})
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
