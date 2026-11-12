package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// jsonResponse writes a JSON response with the given status code.
func jsonResponse(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

// handleError writes a JSON error response for common errors.
func handleError(w http.ResponseWriter, err error) {
	if err == ErrNotFound {
		jsonResponse(w, http.StatusNotFound, map[string]string{"error": "book not found"})
		return
	}
	jsonResponse(w, http.StatusInternalServerError, map[string]string{"error": "internal server error"})
}

// booksHandler is the main HTTP handler that routes requests.
func booksHandler(db *Database) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		path := strings.TrimPrefix(r.URL.Path, "/books")
		path = strings.TrimPrefix(path, "/")

		if path == "" {
			switch r.Method {
			case http.MethodGet:
				listBooks(db, w, r)
			case http.MethodPost:
				createBook(db, w, r)
			default:
				jsonResponse(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			}
			return
		}

		// /books/{id}
		id, err := strconv.ParseInt(path, 10, 64)
		if err != nil {
			jsonResponse(w, http.StatusBadRequest, map[string]string{"error": "invalid book id"})
			return
		}

		switch r.Method {
		case http.MethodGet:
			getBook(db, w, r, id)
		case http.MethodPut:
			updateBook(db, w, r, id)
		case http.MethodDelete:
			deleteBook(db, w, r, id)
		default:
			jsonResponse(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		}
	}
}

// createBook handles POST /books.
func createBook(db *Database, w http.ResponseWriter, r *http.Request) {
	var input struct {
		Title string `json:"title"`
		Author string `json:"author"`
		Year  int    `json:"year"`
		ISBN  string `json:"isbn"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		jsonResponse(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
		return
	}
	if err := validateCreateBook(input.Title, input.Author); err != nil {
		jsonResponse(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	book, err := db.CreateBook(input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		handleError(w, err)
		return
	}
	jsonResponse(w, http.StatusCreated, book)
}

// validateCreateBook checks required fields.
func validateCreateBook(title, author string) error {
	if strings.TrimSpace(title) == "" {
		return errors.New("title is required")
	}
	if strings.TrimSpace(author) == "" {
		return errors.New("author is required")
	}
	return nil
}

// listBooks handles GET /books with optional ?author= filter.
func listBooks(db *Database, w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := db.ListBooks(author)
	if err != nil {
		handleError(w, err)
		return
	}
	if books == nil {
		books = []Book{}
	}
	jsonResponse(w, http.StatusOK, books)
}

// getBook handles GET /books/{id}.
func getBook(db *Database, w http.ResponseWriter, r *http.Request, id int64) {
	book, err := db.GetBook(id)
	if err != nil {
		handleError(w, err)
		return
	}
	jsonResponse(w, http.StatusOK, book)
}

// updateBook handles PUT /books/{id}.
func updateBook(db *Database, w http.ResponseWriter, r *http.Request, id int64) {
	var input struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		ISBN   string `json:"isbn"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		jsonResponse(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
		return
	}
	if err := validateCreateBook(input.Title, input.Author); err != nil {
		jsonResponse(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	book, err := db.UpdateBook(id, input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		handleError(w, err)
		return
	}
	jsonResponse(w, http.StatusOK, book)
}

// deleteBook handles DELETE /books/{id}.
func deleteBook(db *Database, w http.ResponseWriter, r *http.Request, id int64) {
	if err := db.DeleteBook(id); err != nil {
		handleError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
