package main

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

// Handler handles HTTP requests for the book API
type Handler struct {
	db BookStore
}

// createBook handles POST /books
func (h *Handler) createBook(w http.ResponseWriter, r *http.Request) {
	var book Book

	// Parse the request body
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if book.Title == "" {
		http.Error(w, "Title is required", http.StatusBadRequest)
		return
	}
	if book.Author == "" {
		http.Error(w, "Author is required", http.StatusBadRequest)
		return
	}

	// Save the book
	if err := h.db.CreateBook(&book); err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	// Return the created book with ID
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// getBooks handles GET /books with optional author filter
func (h *Handler) getBooks(w http.ResponseWriter, r *http.Request) {
	// Get the author query parameter
	author := r.URL.Query().Get("author")

	// Get books from the database
	books, err := h.db.GetBooks(author)
	if err != nil {
		http.Error(w, "Failed to retrieve books", http.StatusInternalServerError)
		return
	}

	// Return the books
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

// getBook handles GET /books/{id}
func (h *Handler) getBook(w http.ResponseWriter, r *http.Request) {
	// Get the book ID from the URL
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Get the book from the database
	book, err := h.db.GetBook(id)
	if err != nil {
		if err.Error() == "sql: no rows in result set" {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to retrieve book", http.StatusInternalServerError)
		}
		return
	}

	// Return the book
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// updateBook handles PUT /books/{id}
func (h *Handler) updateBook(w http.ResponseWriter, r *http.Request) {
	// Get the book ID from the URL
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Parse the request body
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if book.Title == "" {
		http.Error(w, "Title is required", http.StatusBadRequest)
		return
	}
	if book.Author == "" {
		http.Error(w, "Author is required", http.StatusBadRequest)
		return
	}

	// Update the book in the database
	if err := h.db.UpdateBook(id, &book); err != nil {
		if err.Error() == "sql: no rows in result set" {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to update book", http.StatusInternalServerError)
		}
		return
	}

	// Return the updated book
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// deleteBook handles DELETE /books/{id}
func (h *Handler) deleteBook(w http.ResponseWriter, r *http.Request) {
	// Get the book ID from the URL
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	// Delete the book from the database
	if err := h.db.DeleteBook(id); err != nil {
		if err.Error() == "sql: no rows in result set" {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		}
		return
	}

	// Return success response
	w.WriteHeader(http.StatusNoContent)
}

// healthCheck handles GET /health
func (h *Handler) healthCheck(w http.ResponseWriter, r *http.Request) {
	if err := h.db.HealthCheck(); err != nil {
		http.Error(w, "Database health check failed", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}