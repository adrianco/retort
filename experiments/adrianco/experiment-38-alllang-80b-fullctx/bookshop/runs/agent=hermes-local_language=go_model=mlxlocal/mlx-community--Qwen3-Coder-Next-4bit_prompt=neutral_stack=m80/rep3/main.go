package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type HealthResponse struct {
	Status string `json:"status"`
}

type APIHandler struct {
	db *sql.DB
}

func NewAPIHandler(db *sql.DB) *APIHandler {
	return &APIHandler{db: db}
}

func dbConnect() (*sql.DB, error) {
	db, err := sql.Open("sqlite3", "./books.db")
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	return db, nil
}

func initDB() error {
	db, err := dbConnect()
	if err != nil {
		return err
	}
	defer db.Close()

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return err
	}
	return nil
}

func validateBook(book *Book) error {
	if strings.TrimSpace(book.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(book.Author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

func (h *APIHandler) booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		authorFilter := r.URL.Query().Get("author")
		if authorFilter != "" {
			h.getBooksByAuthor(w, r, authorFilter)
		} else {
			h.getAllBooks(w, r)
		}
	case http.MethodPost:
		h.createBook(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (h *APIHandler) bookHandler(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
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
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (h *APIHandler) getAllBooks(w http.ResponseWriter, r *http.Request) {
	query := "SELECT id, title, author, year, isbn FROM books"
	rows, err := h.db.Query(query)
	if err != nil {
		http.Error(w, fmt.Sprintf("Query error: %v", err), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			http.Error(w, fmt.Sprintf("Scan error: %v", err), http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	if err := rows.Err(); err != nil {
		http.Error(w, fmt.Sprintf("Row error: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func (h *APIHandler) getBooksByAuthor(w http.ResponseWriter, r *http.Request, author string) {
	query := "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
	rows, err := h.db.Query(query, author)
	if err != nil {
		http.Error(w, fmt.Sprintf("Query error: %v", err), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			http.Error(w, fmt.Sprintf("Scan error: %v", err), http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	if err := rows.Err(); err != nil {
		http.Error(w, fmt.Sprintf("Row error: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func (h *APIHandler) getBook(w http.ResponseWriter, r *http.Request, id int) {
	query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
	var book Book
	err := h.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err == sql.ErrNoRows {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}
	if err != nil {
		http.Error(w, fmt.Sprintf("Query error: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func (h *APIHandler) createBook(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if err := validateBook(&book); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
	result, err := h.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		http.Error(w, fmt.Sprintf("Insert error: %v", err), http.StatusInternalServerError)
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		http.Error(w, fmt.Sprintf("LastInsertId error: %v", err), http.StatusInternalServerError)
		return
	}

	book.ID = int(id)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func (h *APIHandler) updateBook(w http.ResponseWriter, r *http.Request, id int) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if err := validateBook(&book); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	query := "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
	result, err := h.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		http.Error(w, fmt.Sprintf("Update error: %v", err), http.StatusInternalServerError)
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		http.Error(w, fmt.Sprintf("RowsAffected error: %v", err), http.StatusInternalServerError)
		return
	}

	if rowsAffected == 0 {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func (h *APIHandler) deleteBook(w http.ResponseWriter, r *http.Request, id int) {
	query := "DELETE FROM books WHERE id = ?"
	result, err := h.db.Exec(query, id)
	if err != nil {
		http.Error(w, fmt.Sprintf("Delete error: %v", err), http.StatusInternalServerError)
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		http.Error(w, fmt.Sprintf("RowsAffected error: %v", err), http.StatusInternalServerError)
		return
	}

	if rowsAffected == 0 {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *APIHandler) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(HealthResponse{Status: "ok"})
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}

	db, err := dbConnect()
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	handler := NewAPIHandler(db)

	http.HandleFunc("/health", handler.healthHandler)
	http.HandleFunc("/books", handler.booksHandler)
	http.HandleFunc("/books/", handler.bookHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Server starting on port %s\n", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
