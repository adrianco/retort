package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type UpdateBookRequest struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

var db *sql.DB

func initDB() error {
	var err error
	db, err = sql.Open("sqlite", ":memory:")
	if err != nil {
		return err
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`

	_, err = db.Exec(createTable)
	return err
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "healthy"})
}

func createBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON")
		return
	}

	if strings.TrimSpace(req.Title) == "" {
		writeError(w, http.StatusBadRequest, "Title is required")
		return
	}
	if strings.TrimSpace(req.Author) == "" {
		writeError(w, http.StatusBadRequest, "Author is required")
		return
	}
	if req.Year == 0 {
		writeError(w, http.StatusBadRequest, "Year is required")
		return
	}
	if strings.TrimSpace(req.ISBN) == "" {
		writeError(w, http.StatusBadRequest, "ISBN is required")
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to create book")
		return
	}

	id, _ := result.LastInsertId()
	book := Book{
		ID:     id,
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	writeJSON(w, http.StatusCreated, book)
}

func listBooksHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	authorFilter := r.URL.Query().Get("author")

	var books []Book
	if authorFilter != "" {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", authorFilter)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "Failed to list books")
			return
		}
		defer rows.Close()
		books = []Book{}
		for rows.Next() {
			var b Book
			if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
				writeError(w, http.StatusInternalServerError, "Failed to scan book")
				return
			}
			books = append(books, b)
		}
	} else {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books")
		if err != nil {
			writeError(w, http.StatusInternalServerError, "Failed to list books")
			return
		}
		defer rows.Close()
		books = []Book{}
		for rows.Next() {
			var b Book
			if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
				writeError(w, http.StatusInternalServerError, "Failed to scan book")
				return
			}
			books = append(books, b)
		}
	}

	if books == nil {
		books = []Book{}
	}

	writeJSON(w, http.StatusOK, books)
}

func getBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var book Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN,
	)
	if err == sql.ErrNoRows {
		writeError(w, http.StatusNotFound, "Book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to get book")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON")
		return
	}

	// Check book exists
	var exists int
	err = db.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&exists)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to check book")
		return
	}
	if exists == 0 {
		writeError(w, http.StatusNotFound, "Book not found")
		return
	}

	// Build update query dynamically
	updates := []string{}
	args := []interface{}{}
	if req.Title != nil {
		if strings.TrimSpace(*req.Title) == "" {
			writeError(w, http.StatusBadRequest, "Title cannot be empty")
			return
		}
		updates = append(updates, "title = ?")
		args = append(args, *req.Title)
	}
	if req.Author != nil {
		if strings.TrimSpace(*req.Author) == "" {
			writeError(w, http.StatusBadRequest, "Author cannot be empty")
			return
		}
		updates = append(updates, "author = ?")
		args = append(args, *req.Author)
	}
	if req.Year != nil {
		if *req.Year == 0 {
			writeError(w, http.StatusBadRequest, "Year cannot be zero")
			return
		}
		updates = append(updates, "year = ?")
		args = append(args, *req.Year)
	}
	if req.ISBN != nil {
		if strings.TrimSpace(*req.ISBN) == "" {
			writeError(w, http.StatusBadRequest, "ISBN cannot be empty")
			return
		}
		updates = append(updates, "isbn = ?")
		args = append(args, *req.ISBN)
	}

	if len(updates) == 0 {
		writeError(w, http.StatusBadRequest, "No fields to update")
		return
	}

	args = append(args, id)
	query := fmt.Sprintf("UPDATE books SET %s WHERE id = ?", strings.Join(updates, ", "))
	_, err = db.Exec(query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to update book")
		return
	}

	// Return updated book
	var book Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to get updated book")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to delete book")
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		writeError(w, http.StatusNotFound, "Book not found")
		return
	}

	writeJSON(w, http.StatusNoContent, nil)
}

func booksHandler(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	// /books with no trailing slash or exact match
	if path == "/books" || path == "/books/" {
		switch r.Method {
		case http.MethodGet:
			listBooksHandler(w, r)
		case http.MethodPost:
			createBookHandler(w, r)
		default:
			writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		}
		return
	}

	// /books/{id}
	if strings.HasPrefix(path, "/books/") {
		idStr := strings.TrimPrefix(path, "/books/")
		if idStr == "" {
			writeError(w, http.StatusBadRequest, "Book ID required")
			return
		}
		// Check if it's a valid ID
		if _, err := strconv.ParseInt(idStr, 10, 64); err != nil {
			writeError(w, http.StatusBadRequest, "Invalid book ID")
			return
		}
		switch r.Method {
		case http.MethodGet:
			getBookHandler(w, r)
		case http.MethodPut:
			updateBookHandler(w, r)
		case http.MethodDelete:
			deleteBookHandler(w, r)
		default:
			writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		}
		return
	}

	writeError(w, http.StatusNotFound, "Not found")
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/books", booksHandler)
	http.HandleFunc("/books/", booksHandler)

	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
