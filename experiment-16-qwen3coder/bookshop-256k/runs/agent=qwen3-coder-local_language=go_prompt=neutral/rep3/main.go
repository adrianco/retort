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
	Isbn   string `json:"isbn"`
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

func (bs *BookStore) CreateBook(book Book) (Book, error) {
	// Validate required fields
	if book.Title == "" {
		return book, fmt.Errorf("title is required")
	}
	if book.Author == "" {
		return book, fmt.Errorf("author is required")
	}

	// Insert into database
	result, err := bs.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		book.Title, book.Author, book.Year, book.Isbn)
	if err != nil {
		return book, err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return book, err
	}

	book.ID = int(id)
	return book, nil
}

func (bs *BookStore) GetAllBooks(author string) ([]Book, error) {
	var books []Book
	var query string
	var args []interface{}

	if author != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?`
		args = append(args, "%"+author+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books`
	}

	rows, err := bs.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}

	return books, nil
}

func (bs *BookStore) GetBookByID(id int) (*Book, error) {
	var book Book
	err := bs.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.Isbn)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book not found")
		}
		return nil, err
	}
	return &book, nil
}

func (bs *BookStore) UpdateBook(id int, book Book) error {
	// Validate required fields
	if book.Title == "" {
		return fmt.Errorf("title is required")
	}
	if book.Author == "" {
		return fmt.Errorf("author is required")
	}

	// Check if book exists
	_, err := bs.GetBookByID(id)
	if err != nil {
		return err
	}

	// Update in database
	_, err = bs.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		book.Title, book.Author, book.Year, book.Isbn, id)
	if err != nil {
		return err
	}

	return nil
}

func (bs *BookStore) DeleteBook(id int) error {
	// Check if book exists
	_, err := bs.GetBookByID(id)
	if err != nil {
		return err
	}

	// Delete from database
	_, err = bs.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}

	return nil
}

func (bs *BookStore) HealthCheck() error {
	return bs.db.Ping()
}

func main() {
	store, err := NewBookStore()
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer store.Close()

	// Set up routes
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
		// Extract ID from URL path
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
		if err := store.HealthCheck(); err != nil {
			http.Error(w, "Service unhealthy", http.StatusServiceUnavailable)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	})

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func handleCreateBook(w http.ResponseWriter, r *http.Request, store *BookStore) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	createdBook, err := store.CreateBook(book)
	if err != nil {
		if strings.Contains(err.Error(), "title is required") || strings.Contains(err.Error(), "author is required") {
			http.Error(w, err.Error(), http.StatusBadRequest)
		} else {
			http.Error(w, "Failed to create book", http.StatusInternalServerError)
		}
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(createdBook)
}

func handleGetBooks(w http.ResponseWriter, r *http.Request, store *BookStore) {
	author := r.URL.Query().Get("author")
	books, err := store.GetAllBooks(author)
	if err != nil {
		http.Error(w, "Failed to retrieve books", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func handleGetBook(w http.ResponseWriter, r *http.Request, store *BookStore, id int) {
	book, err := store.GetBookByID(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to retrieve book", http.StatusInternalServerError)
		}
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

	err := store.UpdateBook(id, book)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else if strings.Contains(err.Error(), "title is required") || strings.Contains(err.Error(), "author is required") {
			http.Error(w, err.Error(), http.StatusBadRequest)
		} else {
			http.Error(w, "Failed to update book", http.StatusInternalServerError)
		}
		return
	}

	updatedBook, err := store.GetBookByID(id)
	if err != nil {
		http.Error(w, "Failed to retrieve updated book", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(updatedBook)
}

func handleDeleteBook(w http.ResponseWriter, r *http.Request, store *BookStore, id int) {
	err := store.DeleteBook(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, "Book not found", http.StatusNotFound)
		} else {
			http.Error(w, "Failed to delete book", http.StatusInternalServerError)
		}
		return
	}

	w.WriteHeader(http.StatusNoContent)
}