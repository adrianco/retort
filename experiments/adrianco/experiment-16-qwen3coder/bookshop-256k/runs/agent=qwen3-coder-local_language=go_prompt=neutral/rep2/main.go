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
		return nil, err
	}

	return &BookStore{db: db}, nil
}

func (bs *BookStore) Close() {
	bs.db.Close()
}

func (bs *BookStore) CreateBook(book Book) (Book, error) {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id`
	err := bs.db.QueryRow(query, book.Title, book.Author, book.Year, book.ISBN).Scan(&book.ID)
	if err != nil {
		return book, err
	}
	return book, nil
}

func (bs *BookStore) GetBooks(author string) ([]Book, error) {
	var query string
	var args []interface{}

	if author != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?`
		args = []interface{}{fmt.Sprintf("%%%s%%", author)}
	} else {
		query = `SELECT id, title, author, year, isbn FROM books`
		args = []interface{}{}
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

func (bs *BookStore) GetBook(id int) (*Book, error) {
	var book Book
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err := bs.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		return nil, err
	}
	return &book, nil
}

func (bs *BookStore) UpdateBook(id int, book Book) error {
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err := bs.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	return err
}

func (bs *BookStore) DeleteBook(id int) error {
	query := `DELETE FROM books WHERE id = ?`
	_, err := bs.db.Exec(query, id)
	return err
}

func (bs *BookStore) HealthCheck() error {
	return bs.db.Ping()
}

func main() {
	bookStore, err := NewBookStore()
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer bookStore.Close()

	// Define routes
	http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case "POST":
			createBookHandler(bookStore, w, r)
		case "GET":
			getBooksHandler(bookStore, w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		// Extract ID from URL path
		path := strings.TrimPrefix(r.URL.Path, "/books/")
		id, err := strconv.Atoi(path)
		if err != nil {
			http.Error(w, "Invalid book ID", http.StatusBadRequest)
			return
		}

		switch r.Method {
		case "GET":
			getBookHandler(bookStore, w, r, id)
		case "PUT":
			updateBookHandler(bookStore, w, r, id)
		case "DELETE":
			deleteBookHandler(bookStore, w, r, id)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		err := bookStore.HealthCheck()
		if err != nil {
			http.Error(w, "Service unhealthy", http.StatusServiceUnavailable)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	})

	fmt.Println("Starting server on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func createBookHandler(bs *BookStore, w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	createdBook, err := bs.CreateBook(book)
	if err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(createdBook)
}

func getBooksHandler(bs *BookStore, w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	books, err := bs.GetBooks(author)
	if err != nil {
		http.Error(w, "Failed to retrieve books", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func getBookHandler(bs *BookStore, w http.ResponseWriter, r *http.Request, id int) {
	book, err := bs.GetBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
			return
		}
		http.Error(w, "Failed to retrieve book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func updateBookHandler(bs *BookStore, w http.ResponseWriter, r *http.Request, id int) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	err := bs.UpdateBook(id, book)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
			return
		}
		http.Error(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func deleteBookHandler(bs *BookStore, w http.ResponseWriter, r *http.Request, id int) {
	err := bs.DeleteBook(id)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Book not found", http.StatusNotFound)
			return
		}
		http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}