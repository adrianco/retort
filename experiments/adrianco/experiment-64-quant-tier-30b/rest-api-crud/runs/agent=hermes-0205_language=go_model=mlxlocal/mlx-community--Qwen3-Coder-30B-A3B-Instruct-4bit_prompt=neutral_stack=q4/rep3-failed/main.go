package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// Book represents a book with its details
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// SQLiteDB handles database operations
type SQLiteDB struct {
	db *sql.DB
}

// Init initializes the database connection
func (db *SQLiteDB) Init(dbPath string) error {
	var err error
 db.db, err = sql.Open("sqlite3", dbPath)
 if err != nil {
 return err
 }

 // Create the books table if it doesn't exist
 createTableSQL := `
CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 year INTEGER,
 isbn TEXT
)`
 _, err = db.db.Exec(createTableSQL)
 if err != nil {
 return err
 }

 return nil
}

// Close closes the database connection
func (db *SQLiteDB) Close() error {
 return db.db.Close()
}

// GetAllBooks gets all books, optionally filtered by author
func (db *SQLiteDB) GetAllBooks(author string) ([]Book, error) {
 var books []Book
 var query string
 var args []interface{}

 if author != "" {
 query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
 args = []interface{}{author}
 } else {
 query = "SELECT id, title, author, year, isbn FROM books"
 }

 rows, err := db.db.Query(query, args...)
 if err != nil {
 return nil, err
 }

 defer rows.Close()

 for rows.Next() {
 var book Book
 err = rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 return nil, err
 }
 books = append(books, book)
 }

 return books, nil
}

// GetBook gets a single book by ID
func (db *SQLiteDB) GetBook(id int) (*Book, error) {
 var book Book
 query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
 err := db.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 return nil, err
 }
 return &book, nil
}

// CreateBook creates a new book in the database
func (db *SQLiteDB) CreateBook(book *Book) error {
 query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
 _, err := db.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
 return err
}

// UpdateBook updates an existing book in the database
func (db *SQLiteDB) UpdateBook(id int, book *Book) error {
 query := "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?"
 _, err := db.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
 return err
}

// DeleteBook deletes a book from the database
func (db *SQLiteDB) DeleteBook(id int) error {
 query := "DELETE FROM books WHERE id=?"
 _, err := db.db.Exec(query, id)
 return err
}

// BookAPI handles HTTP requests for the book API
type BookAPI struct {
 db *SQLiteDB
}

// NewBookAPI creates a new BookAPI instance
func NewBookAPI(dbPath string) (*BookAPI, error) {
 api := &BookAPI{
 db: &SQLiteDB{},
 }
 err := api.db.Init(dbPath)
 if err != nil {
 return nil, err
 }
 return api, nil
}

// HealthHandler handles health check requests
func (api *BookAPI) HealthHandler(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// CreateBook handles POST requests to create new books
func (api *BookAPI) CreateBook(w http.ResponseWriter, r *http.Request) {
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

 err := api.db.CreateBook(&book)
 if err != nil {
 http.Error(w, "Failed to create book: "+err.Error(), http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(book)
}

// GetAllBooks handles GET requests to get all books (with optional author filter)
func (api *BookAPI) GetAllBooks(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 w.Header().Set("Access-Control-Allow-Origin", "*")

 author := r.URL.Query().Get("author")
 books, err := api.db.GetAllBooks(author)
 if err != nil {
 http.Error(w, "Failed to fetch books: "+err.Error(), http.StatusInternalServerError)
 return
 }

 json.NewEncoder(w).Encode(books)
}

// GetBook handles GET requests to get a single book by ID
func (api *BookAPI) GetBook(w http.ResponseWriter, r *http.Request) {
 pathParts := strings.Split(r.URL.Path, "/")
 if len(pathParts) < 3 {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 id, err := strconv.Atoi(pathParts[2])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 book, err := api.db.GetBook(id)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// UpdateBook handles PUT requests to update an existing book
func (api *BookAPI) UpdateBook(w http.ResponseWriter, r *http.Request) {
 pathParts := strings.Split(r.URL.Path, "/")
 if len(pathParts) < 3 {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 id, err := strconv.Atoi(pathParts[2])
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

 err = api.db.UpdateBook(id, &book)
 if err != nil {
 http.Error(w, "Failed to update book: "+err.Error(), http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// DeleteBook handles DELETE requests to delete a book
func (api *BookAPI) DeleteBook(w http.ResponseWriter, r *http.Request) {
 pathParts := strings.Split(r.URL.Path, "/")
 if len(pathParts) < 3 {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 id, err := strconv.Atoi(pathParts[2])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 err = api.db.DeleteBook(id)
 if err != nil {
 http.Error(w, "Failed to delete book: "+err.Error(), http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(map[string]string{"message": "Book deleted successfully"})
}

// main function sets up the HTTP server
func main() {
 api, err := NewBookAPI("books.db")
 if err != nil {
 log.Fatal(err)
 }

 defer api.db.Close()

 r := http.NewServeMux()
 r.HandleFunc("/health", api.HealthHandler)
 r.HandleFunc("/books", api.CreateBook)
 r.HandleFunc("/books/", api.GetBook)
 r.HandleFunc("/books/", api.UpdateBook)
 r.HandleFunc("/books/", api.DeleteBook)

 log.Println("Server starting on port 8080...")
 http.ListenAndServe(":8080", r)
}