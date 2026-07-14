package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

// App holds the repository and provides HTTP handler methods.
type App struct {
	Repo *BookRepository
}

// HealthCheck handles GET /health.
func (a *App) HealthCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// handleBooks handles GET /books and POST /books.
func (a *App) handleBooks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		a.listBooks(w, r)
	case http.MethodPost:
		a.createBook(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// listBooks handles GET /books?author=...
func (a *App) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")

	books, err := a.Repo.GetAllBooks(author)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	if books == nil {
		books = []*Book{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

// createBook handles POST /books
func (a *App) createBook(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if err := book.Validate(); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"error": err.Error(),
		})
		return
	}

	if err := a.Repo.CreateBook(&book); err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			http.Error(w, "Book with this ISBN already exists", http.StatusConflict)
			return
		}
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// handleBookByID handles GET, PUT, DELETE /books/{id}
func (a *App) handleBookByID(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		a.getBook(w, r, id)
	case http.MethodPut:
		a.updateBook(w, r, id)
	case http.MethodDelete:
		a.deleteBook(w, r, id)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// getBook handles GET /books/{id}
func (a *App) getBook(w http.ResponseWriter, r *http.Request, id int) {
	book, err := a.Repo.GetBookByID(id)
	if err == nil {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(book)
		return
	}
	if err.Error() == "no rows in result set" || err.Error() == "SQLITE_ERROR: no such table: books" {
		// For initial startup before schema exists
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	http.Error(w, "Book not found", http.StatusNotFound)
}

// updateBook handles PUT /books/{id}
func (a *App) updateBook(w http.ResponseWriter, r *http.Request, id int) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	book.ID = id

	if err := book.Validate(); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"error": err.Error(),
		})
		return
	}

	if err := a.Repo.UpdateBook(&book); err != nil {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

// deleteBook handles DELETE /books/{id}
func (a *App) deleteBook(w http.ResponseWriter, r *http.Request, id int) {
	if err := a.Repo.DeleteBook(id); err != nil {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
