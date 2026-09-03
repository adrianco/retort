package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID    int    `json:"id"`
	Title string `json:"title"`
	Author string `json:"author"`
	Year  int    `json:"year"`
	ISBN  string `json:"isbn"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore() *BookStore {
	db, err := sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	// Create tables if they don't exist
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
	 author TEXT NOT NULL,
	 year INTEGER,
	 isbn TEXT
	)`)

	if err != nil {
		log.Fatal("Failed to create table:", err)
	}

	return &BookStore{db: db}
}

func (bs *BookStore) Close() {
 bs.db.Close()
}

func (bs *BookStore) CreateBook(w http.ResponseWriter, r *http.Request) {
 var book Book
 if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 if book.Title == "" || book.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 // Check if ISBN is already used
 var existingID int
 err := bs.db.QueryRow("SELECT id FROM books WHERE isbn = ?", book.ISBN).Scan(&existingID)
 if err == nil {
 http.Error(w, "Book with this ISBN already exists", http.StatusConflict)
 return
 }

 // Insert the new book
 _, err = bs.db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
 if err != nil {
 http.Error(w, "Failed to create book", http.StatusInternalServerError)
 return
 }

 // Retrieve the created book
 err = bs.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE title = ? AND author = ? ORDER BY id DESC LIMIT 1", book.Title, book.Author).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 http.Error(w, "Failed to retrieve created book", http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(book)
}

func (bs *BookStore) GetBooks(w http.ResponseWriter, r *http.Request) {
 // Handle query parameters
 query := "SELECT id, title, author, year, isbn FROM books"
 params := []interface{}{}

 // Check if author filter is provided
 author := r.URL.Query().Get("author")
 if author != "" {
 query += " WHERE author = ?"
 params = append(params, author)
 }

 // Check if year filter is provided
 year := r.URL.Query().Get("year")
 if year != "" {
 query += " AND year = ?"
 params = append(params, year)
 }

 rows, err := bs.db.Query(query, params...)
 if err != nil {
 http.Error(w, "Failed to query books", http.StatusInternalServerError)
 return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
 var book Book
 err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 http.Error(w, "Failed to scan book", http.StatusInternalServerError)
 return
 }
 books = append(books, book)
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(books)
}

func (bs *BookStore) GetBook(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/"):]

 bookID, err := strconv.Atoi(id)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 err = bs.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", bookID).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 if err == sql.ErrNoRows {
 http.Error(w, "Book not found", http.StatusNotFound)
 } else {
 http.Error(w, "Failed to get book", http.StatusInternalServerError)
 }
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func (bs *BookStore) UpdateBook(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/"):]

 bookID, err := strconv.Atoi(id)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var book Book
 if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Check if the book exists
 var existingID int
 err = bs.db.QueryRow("SELECT id FROM books WHERE id = ?", bookID).Scan(&existingID)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 // Check if ISBN is already used by another book
 var otherBookID int
 err = bs.db.QueryRow("SELECT id FROM books WHERE isbn = ? AND id != ?", book.ISBN, bookID).Scan(&otherBookID)
 if err == nil {
 http.Error(w, "Book with this ISBN already exists", http.StatusConflict)
 return
 }

 // Update the book
 _, err = bs.db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", book.Title, book.Author, book.Year, book.ISBN, bookID)
 if err != nil {
 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 return
 }

 // Retrieve the updated book
 err = bs.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", bookID).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 http.Error(w, "Failed to retrieve updated book", http.StatusInternalServerError)
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

func (bs *BookStore) DeleteBook(w http.ResponseWriter, r *http.Request) {
 id := r.URL.Path[len("/books/"):]

 bookID, err := strconv.Atoi(id)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 _, err = bs.db.Exec("DELETE FROM books WHERE id = ?", bookID)
 if err != nil {
 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 return
 }

 w.WriteHeader(http.StatusNoContent)
}

func (bs *BookStore) HealthCheck(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func main() {
 store := NewBookStore()
 defer store.Close()

 http.HandleFunc("/health", store.HealthCheck)
 http.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
 switch r.Method {
 case http.MethodGet:
 store.GetBooks(w, r)
 case http.MethodPost:
 store.CreateBook(w, r)
 default:
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
 })

 http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
 switch r.Method {
 case http.MethodGet:
 store.GetBook(w, r)
 case http.MethodPut:
 store.UpdateBook(w, r)
 case http.MethodDelete:
 store.DeleteBook(w, r)
 default:
 http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
 }
 })

 fmt.Println("Book API server running on port 8080")
 log.Fatal(http.ListenAndServe(":8080", nil))
}