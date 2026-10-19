package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID    int    `json:"id"`
	Title string `json:"title"`
	Author string `json:"author"`
	Year  int    `json:"year"`
	ISBN  string `json:"isbn"`
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
var dbFile string = "./books.db"

func initDB() error {
	var err error
	db, err = sql.Open("sqlite3", dbFile)
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

func jsonResponse(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func jsonError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{"error": message})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	jsonResponse(w, http.StatusOK, map[string]string{"status": "ok"})
}

func createBook(w http.ResponseWriter, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Validate required fields
	if strings.TrimSpace(req.Title) == "" {
		jsonError(w, http.StatusBadRequest, "Title is required")
		return
	}
	if strings.TrimSpace(req.Author) == "" {
		jsonError(w, http.StatusBadRequest, "Author is required")
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		jsonError(w, http.StatusInternalServerError, "Failed to create book")
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

func listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")

	var rows *sql.Rows
	var err error

	if author != "" {
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
	} else {
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
	}

	if err != nil {
		jsonError(w, http.StatusInternalServerError, "Failed to fetch books")
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			jsonError(w, http.StatusInternalServerError, "Failed to parse book")
			return
		}
		books = append(books, b)
	}

	if books == nil {
		books = []Book{}
	}

	jsonResponse(w, http.StatusOK, books)
}

func getBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		jsonError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var b Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

	if err == sql.ErrNoRows {
		jsonError(w, http.StatusNotFound, "Book not found")
		return
	}
	if err != nil {
		jsonError(w, http.StatusInternalServerError, "Failed to fetch book")
		return
	}

	jsonResponse(w, http.StatusOK, b)
}

func updateBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		jsonError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Check book exists
	var exists int
	err = db.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&exists)
	if err != nil || exists == 0 {
		jsonError(w, http.StatusNotFound, "Book not found")
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
		jsonError(w, http.StatusBadRequest, "No fields to update")
		return
	}

	args = append(args, id)
	query := fmt.Sprintf("UPDATE books SET %s WHERE id = ?", strings.Join(updates, ", "))
	_, err = db.Exec(query, args...)
	if err != nil {
		jsonError(w, http.StatusInternalServerError, "Failed to update book")
		return
	}

	// Fetch updated book
	var b Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		jsonError(w, http.StatusInternalServerError, "Failed to fetch updated book")
		return
	}

	jsonResponse(w, http.StatusOK, b)
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		jsonError(w, http.StatusBadRequest, "Invalid book ID")
		return
	}

	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		jsonError(w, http.StatusInternalServerError, "Failed to delete book")
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		jsonError(w, http.StatusNotFound, "Book not found")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func booksHandler(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	// Handle /books exactly (no trailing path)
	if path == "/books" || path == "/books/" {
		switch r.Method {
		case http.MethodGet:
			listBooks(w, r)
		case http.MethodPost:
			createBook(w, r)
		default:
			jsonError(w, http.StatusMethodNotAllowed, "Method not allowed")
		}
		return
	}

	// Handle /books/{id}
	if strings.HasPrefix(path, "/books/") {
		idPart := strings.TrimPrefix(path, "/books/")
		if idPart != "" {
			switch r.Method {
			case http.MethodGet:
				getBook(w, r)
			case http.MethodPut:
				updateBook(w, r)
			case http.MethodDelete:
				deleteBook(w, r)
			default:
				jsonError(w, http.StatusMethodNotAllowed, "Method not allowed")
			}
			return
		}
	}

	jsonError(w, http.StatusNotFound, "Not found")
}

func main() {
	if err := initDB(); err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer db.Close()

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/books/", booksHandler)
	http.HandleFunc("/books", booksHandler)

	log.Println("Server starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
