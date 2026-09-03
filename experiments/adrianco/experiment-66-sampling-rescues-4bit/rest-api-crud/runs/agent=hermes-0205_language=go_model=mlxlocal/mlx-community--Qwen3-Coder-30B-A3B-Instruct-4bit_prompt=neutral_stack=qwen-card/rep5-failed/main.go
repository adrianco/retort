package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int32  `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookRequest struct {
	Title string `json:"title"`
	Author string `json:"author"`
	Year   int32  `json:"year"`
	ISBN   string `json:"isbn"`
}

var db *sql.DB

func main() {
	var err error
 db, err = sql.Open("sqlite3", "./books.db")
 if err != nil {
 log.Fatal("Failed to connect to database:", err)
 }
 defer db.Close()

 // Create tables if they don't exist
 createTable()

 // Set up routes
 http.HandleFunc("/health", healthCheck)
 http.HandleFunc("/books", handleBooks)
 http.HandleFunc("/books/", handleBook)

 // Start server
 port := os.Getenv("PORT")
 if port == "" {
 port = "8080"
 }
 log.Printf("Server starting on port %s", port)
 log.Fatal(http.ListenAndServe(":"+port, nil))
}

func createTable() {
 _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 year INTEGER,
 isbn TEXT
 )`)
 if err != nil {
 log.Fatal("Failed to create table:", err)
 }
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]interface{}{"status": "healthy"})
}

func handleBooks(w http.ResponseWriter, r *http.Request) {
 switch r.Method {
 case "GET":
 books, err := getAllBooks()
 if err != nil {
 http.Error(w, err.Error(), http.StatusInternalServerError)
 return
 }
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(books)

 case "POST":
 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if bookReq.Title == "" || bookReq.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 // Create new book
 id, err := createBook(bookReq)
 if err != nil {
 http.Error(w, err.Error(), http.StatusInternalServerError)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(map[string]interface{}{"id": id, "message": "Book created successfully"})
 }
}

func handleBook(w http.ResponseWriter, r *http.Request) {
 path := r.URL.Path
 parts := strings.Split(path, "/")
 if len(parts) < 3 {
 http.Error(w, "Invalid path", http.StatusBadRequest)
 return
 }

 id, err := strconv.ParseInt(parts[3], 10, 64)
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 switch r.Method {
 case "GET":
 book, err := getBook(id)
 if err != nil {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)

 case "PUT":
 var bookReq BookRequest
 if err := json.NewDecoder(r.Body).Decode(&bookReq); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if bookReq.Title == "" || bookReq.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 err = updateBook(id, bookReq)
 if err != nil {
 http.Error(w, err.Error(), http.StatusNotFound)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]interface{}{"message": "Book updated successfully"})
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]interface{}{"message": "Book deleted successfully"})
}

func getAllBooks() ([]Book, error) {
 rows, err := db.Query("SELECT id, title, author, year, isbn FROM books")
 if err != nil {
 return nil, err
 }
 defer rows.Close()

 books := []Book{}
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

func getBook(id int64) (*Book, error) {
 row := db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
 book := Book{}
 err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
 return nil, err
 }
 return &book, nil
}

func createBook(bookReq BookRequest) (int64, error) {
 res, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", bookReq.Title, bookReq.Author, bookReq.Year, bookReq.ISBN)
 if err != nil {
 return 0, err
 }

 id, err := res.LastInsertId()
 if err != nil {
 return 0, err
 }

 return id, nil
}

func updateBook(id int64, bookReq BookRequest) error {
 _, err := db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", bookReq.Title, bookReq.Author, bookReq.Year, bookReq.ISBN, id)
 if err != nil {
 return err
 }

 return nil
}

func deleteBook(id int64) error {
 _, err := db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
 return err
 }

 return nil
}