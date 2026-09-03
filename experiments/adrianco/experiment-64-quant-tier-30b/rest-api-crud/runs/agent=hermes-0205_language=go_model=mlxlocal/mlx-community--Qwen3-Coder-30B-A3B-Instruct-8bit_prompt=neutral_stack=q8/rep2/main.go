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

func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
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

func (bs *BookStore) Close() error {
	return bs.db.Close()
}

func (bs *BookStore) CreateBook(book *Book) error {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := bs.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return err
	}
	
	// Get the ID of the newly inserted book
	id, err := result.LastInsertId()
	if err != nil {
		return err
	}
	
	book.ID = int(id)
	return nil
}

func (bs *BookStore) GetAllBooks(authorFilter string) ([]Book, error) {
	var query string
	var args []interface{}

	if authorFilter != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY id`
		args = append(args, "%"+authorFilter+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books ORDER BY id`
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
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	row := bs.db.QueryRow(query, id)

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

func (bs *BookStore) UpdateBook(id int, book *Book) error {
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
	// Initialize database
	store, err := NewBookStore("./books.db")
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	defer store.Close()

	// Set up HTTP handlers
	http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case "POST":
			handleCreateBook(w, r, store)
		case "GET":
			handleGetBooks(w, r, store)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		// Extract ID from the URL path
		path := strings.TrimPrefix(r.URL.Path, "/books/")
		id, err := strconv.Atoi(path)
		if err != nil {
			http.Error(w, "Invalid book ID", http.StatusBadRequest)
			return
		}

		switch r.Method {
		case "GET":
			handleGetBook(w, r, store, id)
		case "PUT":
			handleUpdateBook(w, r, store, id)
		case "DELETE":
			handleDeleteBook(w, r, store, id)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		
		err := store.HealthCheck()
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

func handleCreateBook(w http.ResponseWriter, r *http.Request, store *BookStore) {
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

	if err := store.CreateBook(&book); err != nil {
		http.Error(w, "Failed to create book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func handleGetBooks(w http.ResponseWriter, r *http.Request, store *BookStore) {
	author := r.URL.Query().Get("author")
	books, err := store.GetAllBooks(author)
	if err != nil {
		http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func handleGetBook(w http.ResponseWriter, r *http.Request, store *BookStore, id int) {
	book, err := store.GetBookByID(id)
	if err != nil {
		http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
		return
	}

	if book == nil {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func handleUpdateBook(w http.ResponseWriter, r *http.Request, store *BookStore, id int) {
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

	// Check if book exists
	existingBook, err := store.GetBookByID(id)
	if err != nil {
		http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
		return
	}
	if existingBook == nil {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	if err := store.UpdateBook(id, &book); err != nil {
		http.Error(w, "Failed to update book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func handleDeleteBook(w http.ResponseWriter, r *http.Request, store *BookStore, id int) {
	// Check if book exists
	existingBook, err := store.GetBookByID(id)
	if err != nil {
		http.Error(w, "Failed to check book existence", http.StatusInternalServerError)
		return
	}
	if existingBook == nil {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	if err := store.DeleteBook(id); err != nil {
		http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}