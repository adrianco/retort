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
	ID     int    `json:"id"`
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
	db, err = sql.Open("sqlite", "file:books.db?cache=shared&mode=rwc")
	if err != nil {
		return err
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
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
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
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

	// Validate required fields
	if strings.TrimSpace(req.Title) == "" {
		writeError(w, http.StatusBadRequest, "Title is required")
		return
	}
	if strings.TrimSpace(req.Author) == "" {
		writeError(w, http.StatusBadRequest, "Author is required")
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
		ID:     int(id),
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

	query := "SELECT id, title, author, year, isbn FROM books"
	var args []interface{}

	author := r.URL.Query().Get("author")
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}

	rows, err := db.Query(query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to fetch books")
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "Failed to parse book")
			return
		}
		books = append(books, b)
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
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var b Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		writeError(w, http.StatusNotFound, "Book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to fetch book")
		return
	}

	writeJSON(w, http.StatusOK, b)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
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
	var updates []string
	var args []interface{}
	if req.Title != nil {
		updates = append(updates, "title = ?")
		args = append(args, *req.Title)
	}
	if req.Author != nil {
		updates = append(updates, "author = ?")
		args = append(args, *req.Author)
	}
	if req.Year != nil {
		updates = append(updates, "year = ?")
		args = append(args, *req.Year)
	}
	if req.ISBN != nil {
		updates = append(updates, "isbn = ?")
		args = append(args, *req.ISBN)
	}

	if len(updates) == 0 {
		writeError(w, http.StatusBadRequest, "No fields to update")
		return
	}

	args = append(args, id)
	_, err = db.Exec(fmt.Sprintf("UPDATE books SET %s WHERE id = ?", strings.Join(updates, ", ")), args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to update book")
		return
	}

	// Return updated book
	var b Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to fetch updated book")
		return
	}

	writeJSON(w, http.StatusOK, b)
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
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

	w.WriteHeader(http.StatusNoContent)
}

func booksHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/books")
	if path == "" {
		// /books — list or create
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
	idStr := strings.TrimPrefix(path, "/")
	parts := strings.Split(idStr, "/")
	if len(parts) != 1 || parts[0] == "" {
		writeError(w, http.StatusNotFound, "Not found")
		return
	}
	idStr = parts[0]
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
	log.Fatal(http.ListenAndServe(":8080", nil))
}
