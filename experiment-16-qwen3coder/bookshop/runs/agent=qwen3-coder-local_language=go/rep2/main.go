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

func (bs *BookStore) Close() error {
	return bs.db.Close()
}

func (bs *BookStore) CreateBook(book Book) (Book, error) {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := bs.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return Book{}, err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return Book{}, err
	}

	book.ID = int(id)
	return book, nil
}

func (bs *BookStore) GetBook(id int) (Book, error) {
	var book Book
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err := bs.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		return Book{}, err
	}
	return book, nil
}

func (bs *BookStore) GetAllBooks(author string) ([]Book, error) {
	var books []Book
	var query string
	var rows *sql.Rows
	var err error

	if author != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY title`
		rows, err = bs.db.Query(query, "%"+author+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books ORDER BY title`
		rows, err = bs.db.Query(query)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

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
	store, err := NewBookStore()
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer store.Close()

	mux := http.NewServeMux()

	// Health check endpoint
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := store.HealthCheck(); err != nil {
			http.Error(w, "Database connection failed", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	})

	// POST /books - Create a new book
	mux.HandleFunc("POST /books", func(w http.ResponseWriter, r *http.Request) {
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

		createdBook, err := store.CreateBook(book)
		if err != nil {
			http.Error(w, "Failed to create book", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(createdBook)
	})

	// GET /books - List all books or filter by author
	mux.HandleFunc("GET /books", func(w http.ResponseWriter, r *http.Request) {
		author := r.URL.Query().Get("author")
		books, err := store.GetAllBooks(author)
		if err != nil {
			http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(books)
	})

	// GET /books/{id} - Get a single book by ID
	mux.HandleFunc("GET /books/{id}", func(w http.ResponseWriter, r *http.Request) {
		idStr := strings.TrimPrefix(r.URL.Path, "/books/")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			http.Error(w, "Invalid book ID", http.StatusBadRequest)
			return
		}

		book, err := store.GetBook(id)
		if err != nil {
			if err == sql.ErrNoRows {
				http.Error(w, "Book not found", http.StatusNotFound)
				return
			}
			http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(book)
	})

	// PUT /books/{id} - Update a book
	mux.HandleFunc("PUT /books/{id}", func(w http.ResponseWriter, r *http.Request) {
		idStr := strings.TrimPrefix(r.URL.Path, "/books/")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			http.Error(w, "Invalid book ID", http.StatusBadRequest)
			return
		}

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

		err = store.UpdateBook(id, book)
		if err != nil {
			if err == sql.ErrNoRows {
				http.Error(w, "Book not found", http.StatusNotFound)
				return
			}
			http.Error(w, "Failed to update book", http.StatusInternalServerError)
			return
		}

		updatedBook, err := store.GetBook(id)
		if err != nil {
			http.Error(w, "Failed to fetch updated book", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(updatedBook)
	})

	// DELETE /books/{id} - Delete a book
	mux.HandleFunc("DELETE /books/{id}", func(w http.ResponseWriter, r *http.Request) {
		idStr := strings.TrimPrefix(r.URL.Path, "/books/")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			http.Error(w, "Invalid book ID", http.StatusBadRequest)
			return
		}

		err = store.DeleteBook(id)
		if err != nil {
			if err == sql.ErrNoRows {
				http.Error(w, "Book not found", http.StatusNotFound)
				return
			}
			http.Error(w, "Failed to delete book", http.StatusInternalServerError)
			return
		}

		w.WriteHeader(http.StatusNoContent)
	})

	addr := ":8080"
	fmt.Printf("Starting server on %s\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal("Server failed to start:", err)
	}
}