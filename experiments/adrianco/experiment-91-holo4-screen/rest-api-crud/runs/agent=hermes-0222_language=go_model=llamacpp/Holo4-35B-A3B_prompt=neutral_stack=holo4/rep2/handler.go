package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

var db *sql.DB

func booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		listBooks(w, r)
	case http.MethodPost:
		createBook(w, r)
	default:
		jsonError(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func booksByIDHandler(w http.ResponseWriter, r *http.Request) {
	id, err := extractID(r.URL.Path)
	if err != nil {
		jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		getBook(w, r, id)
	case http.MethodPut:
		updateBook(w, r, id)
	case http.MethodDelete:
		deleteBook(w, r, id)
	default:
		jsonError(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func extractID(path string) (int, error) {
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) < 2 {
		return 0, nil
	}
	id, err := strconv.Atoi(parts[1])
	if err != nil {
		return 0, nil
	}
	return id, nil
}

func listBooks(w http.ResponseWriter, r *http.Request) {
	authorFilter := r.URL.Query().Get("author")

	query := `SELECT id, title, author, year, isbn FROM books`
	args := []interface{}{}
	if authorFilter != "" {
		query += ` WHERE author = ?`
		args = append(args, authorFilter)
	}
	rows, err := db.Query(query, args...)
	if err != nil {
		jsonError(w, "failed to query books", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			jsonError(w, "failed to scan book", http.StatusInternalServerError)
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		jsonError(w, "failed to iterate books", http.StatusInternalServerError)
		return
	}

	if books == nil {
		books = []Book{}
	}

	jsonResponse(w, http.StatusOK, books)
}

func createBook(w http.ResponseWriter, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "invalid JSON body", http.StatusBadRequest)
		return
	}

	if err := validateCreateBook(req); err != nil {
		jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	result, err := db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE constraint failed") {
			jsonError(w, "book with that ISBN already exists", http.StatusConflict)
			return
		}
		jsonError(w, "failed to create book", http.StatusInternalServerError)
		return
	}

	id, _ := result.LastInsertId()
	book := Book{
		ID:     int(id),
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	jsonResponse(w, http.StatusCreated, book)
}

func getBook(w http.ResponseWriter, r *http.Request, id int) {
	var b Book
	err := db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

	if err == sql.ErrNoRows {
		jsonError(w, "book not found", http.StatusNotFound)
		return
	}
	if err != nil {
		jsonError(w, "failed to get book", http.StatusInternalServerError)
		return
	}

	jsonResponse(w, http.StatusOK, b)
}

func updateBook(w http.ResponseWriter, r *http.Request, id int) {
	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "invalid JSON body", http.StatusBadRequest)
		return
	}

	var title, author string
	var year int
	if err := db.QueryRow(
		`SELECT title, author, year FROM books WHERE id = ?`, id,
	).Scan(&title, &author, &year); err == sql.ErrNoRows {
		jsonError(w, "book not found", http.StatusNotFound)
		return
	} else if err != nil {
		jsonError(w, "failed to get book", http.StatusInternalServerError)
		return
	}

	newTitle := req.Title
	if newTitle == nil {
		newTitle = &title
	}
	newAuthor := req.Author
	if newAuthor == nil {
		newAuthor = &author
	}
	newYear := req.Year
	if newYear == nil {
		newYear = &year
	}

	if err := validateUpdateBook(*newTitle, *newAuthor, *newYear); err != nil {
		jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	_, err := db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ? WHERE id = ?`,
		*newTitle, *newAuthor, *newYear, id,
	)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE constraint failed") {
			jsonError(w, "book with that ISBN already exists", http.StatusConflict)
			return
		}
		jsonError(w, "failed to update book", http.StatusInternalServerError)
		return
	}

	jsonResponse(w, http.StatusOK, Book{
		ID:     id,
		Title:  *newTitle,
		Author: *newAuthor,
		Year:   *newYear,
		ISBN:   bookISBNOrDefault(req.ISBN, ""),
	})
}

func bookISBNOrDefault(isbn *string, def string) string {
	if isbn == nil {
		return def
	}
	return *isbn
}

func deleteBook(w http.ResponseWriter, r *http.Request, id int) {
	res, err := db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		jsonError(w, "failed to delete book", http.StatusInternalServerError)
		return
	}

	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		jsonError(w, "book not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		jsonError(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	jsonResponse(w, http.StatusOK, map[string]string{"status": "ok"})
}

func validateCreateBook(req CreateBookRequest) error {
	if strings.TrimSpace(req.Title) == "" {
		return &ValidationError{"title is required"}
	}
	if strings.TrimSpace(req.Author) == "" {
		return &ValidationError{"author is required"}
	}
	return nil
}

func validateUpdateBook(title, author string, year int) error {
	if strings.TrimSpace(title) == "" {
		return &ValidationError{"title is required"}
	}
	if strings.TrimSpace(author) == "" {
		return &ValidationError{"author is required"}
	}
	return nil
}

type ValidationError struct {
	Message string
}

func (e *ValidationError) Error() string { return e.Message }

func jsonResponse(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func jsonError(w http.ResponseWriter, message string, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(ErrorResponse{Error: message})
}
