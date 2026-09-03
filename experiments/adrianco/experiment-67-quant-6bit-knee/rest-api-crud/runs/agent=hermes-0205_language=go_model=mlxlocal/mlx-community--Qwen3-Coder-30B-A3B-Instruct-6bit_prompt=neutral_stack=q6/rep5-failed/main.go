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
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore() (*BookStore, error) {
	db, err := sql.Open("sqlite3", "./books.db")
	if err != nil {
		return nil, err
	}

	// Create books table if it doesn't exist
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	)`)
	if err != nil {
		return nil, err
	}

	return &BookStore{db: db}, nil
}

func (bs *BookStore) Close() {
	bs.db.Close()
}

func (bs *BookStore) CreateBook(book Book) (int, error) {
	result, err := bs.db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return 0, err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return 0, err
	}

	return int(id), nil
}

func (bs *BookStore) GetAllBooks(author string) ([]Book, error) {
	var query string
	var args []interface{}

	if author != "" {
		query = "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?"
		args = append(args, "%"+author+"%")
	} else {
		query = "SELECT id, title, author, year, isbn FROM books"
	}

	rows, err := bs.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}

	return books, nil
}

func (bs *BookStore) GetBookByID(id int) (*Book, error) {
	row := bs.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
	
	var book Book
	err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	return &book, nil
}

func (bs *BookStore) UpdateBook(id int, book Book) error {
	_, err := bs.db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", book.Title, book.Author, book.Year, book.ISBN, id)
	return err
}

func (bs *BookStore) DeleteBook(id int) error {
	_, err := bs.db.Exec("DELETE FROM books WHERE id = ?", id)
	return err
}

func (bs *BookStore) HealthCheck() bool {
	err := bs.db.Ping()
	return err == nil
}

func writeJSON(w http.ResponseWriter, data interface{}, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(data)
}

func (bs *BookStore) HealthHandler(w http.ResponseWriter, r *http.Request) {
	if bs.HealthCheck() {
		writeJSON(w, map[string]string{"status": "healthy"}, http.StatusOK)
	} else {
		writeJSON(w, map[string]string{"status": "unhealthy"}, http.StatusServiceUnavailable)
	}
}

func (bs *BookStore) CreateBookHandler(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		writeJSON(w, map[string]string{"error": "Invalid JSON"}, http.StatusBadRequest)
		return
	}

	// Validation
	if book.Title == "" {
		writeJSON(w, map[string]string{"error": "Title is required"}, http.StatusBadRequest)
		return
	}
	if book.Author == "" {
		writeJSON(w, map[string]string{"error": "Author is required"}, http.StatusBadRequest)
		return
	}

	id, err := bs.CreateBook(book)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to create book"}, http.StatusInternalServerError)
		return
	}

	book.ID = id
	writeJSON(w, book, http.StatusCreated)
}

func (bs *BookStore) GetAllBooksHandler(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := bs.GetAllBooks(author)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to retrieve books"}, http.StatusInternalServerError)
		return
	}

	writeJSON(w, books, http.StatusOK)
}

func (bs *BookStore) GetBookHandler(w http.ResponseWriter, r *http.Request) {
	// Extract ID from path
	path := strings.TrimPrefix(r.URL.Path, "/books/")
	if path == "" {
		writeJSON(w, map[string]string{"error": "Book ID required"}, http.StatusBadRequest)
		return
	}
	
	id, err := strconv.Atoi(path)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Invalid book ID"}, http.StatusBadRequest)
		return
	}

	book, err := bs.GetBookByID(id)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to retrieve book"}, http.StatusInternalServerError)
		return
	}

	if book == nil {
		writeJSON(w, map[string]string{"error": "Book not found"}, http.StatusNotFound)
		return
	}

	writeJSON(w, book, http.StatusOK)
}

func (bs *BookStore) UpdateBookHandler(w http.ResponseWriter, r *http.Request) {
	// Extract ID from path
	path := strings.TrimPrefix(r.URL.Path, "/books/")
	if path == "" {
		writeJSON(w, map[string]string{"error": "Book ID required"}, http.StatusBadRequest)
		return
	}
	
	id, err := strconv.Atoi(path)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Invalid book ID"}, http.StatusBadRequest)
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		writeJSON(w, map[string]string{"error": "Invalid JSON"}, http.StatusBadRequest)
		return
	}

	// Validation
	if book.Title == "" {
		writeJSON(w, map[string]string{"error": "Title is required"}, http.StatusBadRequest)
		return
	}
	if book.Author == "" {
		writeJSON(w, map[string]string{"error": "Author is required"}, http.StatusBadRequest)
		return
	}

	// Check if book exists
	existingBook, err := bs.GetBookByID(id)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to check book"}, http.StatusInternalServerError)
		return
	}
	if existingBook == nil {
		writeJSON(w, map[string]string{"error": "Book not found"}, http.StatusNotFound)
		return
	}

	err = bs.UpdateBook(id, book)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to update book"}, http.StatusInternalServerError)
		return
	}

	book.ID = id
	writeJSON(w, book, http.StatusOK)
}

func (bs *BookStore) DeleteBookHandler(w http.ResponseWriter, r *http.Request) {
	// Extract ID from path
	path := strings.TrimPrefix(r.URL.Path, "/books/")
	if path == "" {
		writeJSON(w, map[string]string{"error": "Book ID required"}, http.StatusBadRequest)
		return
	}
	
	id, err := strconv.Atoi(path)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Invalid book ID"}, http.StatusBadRequest)
		return
	}

	// Check if book exists
	existingBook, err := bs.GetBookByID(id)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to check book"}, http.StatusInternalServerError)
		return
	}
	if existingBook == nil {
		writeJSON(w, map[string]string{"error": "Book not found"}, http.StatusNotFound)
		return
	}

	err = bs.DeleteBook(id)
	if err != nil {
		writeJSON(w, map[string]string{"error": "Failed to delete book"}, http.StatusInternalServerError)
		return
	}

	writeJSON(w, map[string]string{"message": "Book deleted successfully"}, http.StatusOK)
}

func main() {
	// Create database connection
	bookStore, err := NewBookStore()
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	defer bookStore.Close()

	// Setup routes
	http.HandleFunc("/health", bookStore.HealthHandler)
	http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case "POST":
			bookStore.CreateBookHandler(w, r)
		case "GET":
			bookStore.GetAllBooksHandler(w, r)
		default:
			http.NotFound(w, r)
		}
	})

	// Handle GET, PUT, DELETE on /books/{id}
	http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/books/") {
			switch r.Method {
			case "GET":
				bookStore.GetBookHandler(w, r)
			case "PUT":
				bookStore.UpdateBookHandler(w, r)
			case "DELETE":
				bookStore.DeleteBookHandler(w, r)
			default:
				http.NotFound(w, r)
			}
		} else {
			http.NotFound(w, r)
		}
	})

	fmt.Println("Starting server on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}