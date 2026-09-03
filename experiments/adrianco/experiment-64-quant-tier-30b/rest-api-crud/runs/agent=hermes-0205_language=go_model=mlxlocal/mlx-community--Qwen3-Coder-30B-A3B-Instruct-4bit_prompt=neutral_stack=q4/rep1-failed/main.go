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
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID   int   `json:"id"`
	Title string `json:"title"`
	Author string `json:"author"`
	Year int `json:"year"`
	ISBN string `json:"isbn"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, err
	}

	// Create the books table if it doesn't exist
	createTableQuery := `
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
)`
 _, err = db.Exec(createTableQuery)
 if err != nil {
	 return nil, err
 }

 return &BookStore{db: db}, nil
}

func (bs *BookStore) CreateBook(title, author, isbn string, year int) (*Book, error) {
	// Validate required fields
	if title == "" || author == "" {
		return nil, fmt.Errorf("title and author are required")
	}

	// Check if ISBN already exists
	var existingID int
	err := bs.db.QueryRow("SELECT id FROM books WHERE isbn = ?", isbn).Scan(&existingID)
	if err == nil {
		return nil, fmtErrorf("book with ISBN %s already exists", isbn)
	}

	// Create the book
	book := &Book{
		Title: title,
		Author: author,
		Year: year,
		ISBN: isbn,
	}

	// Insert into database
	res, err := bs.db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return nil, err
	}

	// Get the ID of the newly created book
	id, err := res.LastInsertId()
	if err != nil {
		return nil, err
	}

	book.ID = int(id)
	return book, nil
}

func (bs *BookStore) GetAllBooks(authorFilter string) ([]Book, error) {
	var books []Book

	var query string
	var args []interface{}

	if authorFilter != "" {
	 query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
	 args = append(args, authorFilter)
	} else {
	 query = "SELECT id, title, author, year, isbn FROM books"
	}

	rows, err := bs.db.Query(query, args...)
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

func (bs *BookStore) GetBookByID(id int) (*Book, error) {
	var book Book
 err := bs.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
	 return nil, fmt.Errorf("book not found")
 }

 return &book, nil
}

func (bs *BookStore) UpdateBook(id int, title, author, isbn string, year int) (*Book, error) {
	// Validate required fields
	if title == "" || author == "" {
		return nil, fmt.Errorf("title and author are required")
	}

	// Check if book exists
	var existingID int
 err := bs.db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&existingID)
 if err != nil {
	 return nil, fmt.Errorf("book not found")
 }

 // Check if ISBN already exists (excluding current book)
 var isbnExists int
 err = bs.db.QueryRow("SELECT id FROM books WHERE isbn = ? AND id != ?", isbn, id).Scan(&isbnExists)
 if err == nil {
	 return nil, fmt.Errorf("book with ISBN %s already exists", isbn)
 }

	// Update the book
 _, err = bs.db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", 
 title, author, year, isbn, id)
 if err != nil {
 return nil, err
 }

 // Return updated book
 book, err := bs.GetBookByID(id)
 if err != nil {
 return nil, err
 }

 return book, nil
}

func (bs *BookStore) DeleteBook(id int) error {
 _, err := bs.db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 return err
 }

 return nil
}

func main() {
	// Create database connection
 store, err := NewBookStore("books.db")
 if err != nil {
 log.Fatal(err)
 }

 // Start the server
 http.HandleFunc("/health", healthHandler)
 http.HandleFunc("/books", booksHandler)
 http.HandleFunc("/books/", bookHandler)

 port := "8080"
 fmt.Printf("Server starting on port %s\n", port)
 log.Fatal(http.ListenAndServe(":"+port, nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func booksHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case "GET":
		booksHandlerGet(w, r)
	case "POST":
		booksHandlerPost(w, r)
	default:
	 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
}

func bookHandler(w http.ResponseWriter, r *http.Request) {
	// Extract ID from URL
 path := strings.TrimPrefix(r.URL.Path, "/books/")
 id, err := strconv.Atoi(path)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 switch r.Method {
 case "GET":
 getBookHandler(w, r, id)
 case "PUT":
 updateBookHandler(w, r, id)
 case "DELETE":
 deleteBookHandler(w, r, id)
 default:
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
}

func getBookHandler(w http.ResponseWriter, r *http.Request, id int) {
 store, err := NewBookStore("books.db")
 if err != nil {
 http.Error(w, "Internal server error", http.StatusInternalServerError)
 return
 }

 book, err := store.GetBookByID(id)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func getBookByAuthor(w http.ResponseWriter, r *http.Request) {
 store, err := NewBookStore("books.db")
 if err != nil {
 http.Error(w, "Internal server error", http.StatusInternalServerError)
 return
 }

 author := r.URL.Query().Get("author")
 books, err := store.GetAllBooks(author)
 if err != nil {
 http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(books)
}

func booksHandlerGet(w http.ResponseWriter, r *http.Request) {
 store, err := NewBookStore("books.db")
 if err != nil {
 http.Error(w, "Internal server error", http.StatusInternalServerError)
 return
 }

 author := r.URL.Query().Get("author")
 books, err := store.GetAllBooks(author)
 if err != nil {
 http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(books)
}

func booksHandlerPost(w http.ResponseWriter, r *http.Request) {
 store, err := NewBookStore("books.db")
 if err != nil {
 http.Error(w, "Internal server error", http.StatusInternalServerError)
 return
 }

 var book Book
 err = json.NewDecoder(r.Body).Decode(&book)
 if err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 createdBook, err := store.CreateBook(book.Title, book.Author, book.ISBN, book.Year)
 if err != nil {
 http.Error(w, err.Error(), http.StatusBadRequest)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(createdBook)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request, id int) {
 store, err := NewBookStore("books.db")
 if err != nil {
 http.Error(w, "Internal server error", http.StatusInternalServerError)
 return
 }

 var book Book
 err = json.NewDecoder(r.Body).Decode(&book)
 if err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 updatedBook, err := store.UpdateBook(id, book.Title, book.Author, book.ISBN, book.Year)
 if err != nil {
 http.Error(w, err.Error(), http.StatusBadRequest)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(updatedBook)
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request, id int) {
 store, err := NewBookStore("books.db")
 if err != nil {
 http.Error(w, "Internal server error", http.StatusInternalServerError)
 return
 }

 err = store.DeleteBook(id)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}