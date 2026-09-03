package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

// Book represents a book with its details
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// In-memory storage for books
var (
	books   = make(map[int]Book)
	nextID  = 1
)

// Response represents a response structure
type Response struct {
	Message string `json:"message"`
}

// Health check handler
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// Create a new book
func createBook(w http.ResponseWriter, r *http.Request) {
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

	book.ID = nextID
	books[nextID] = book
	nextID++

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(book)
}

// Get all books with optional author filter
func getBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	author := r.URL.Query().Get("author")
	var filteredBooks []Book

	for _, book := range books {
	 if author == "" || author == book.Author {
	 filteredBooks = append(filteredBooks, book)
 }
 }

 json.NewEncoder(w).Encode(filteredBooks)
}

// Get a single book by ID
func getBook(w http.ResponseWriter, r *http.Request) {
	// Extract ID from URL path
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 book, exists := books[id]
 if !exists {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// Update a book
func updateBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 book, exists := books[id]
 if !exists {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 var updatedBook Book
 if err := json.NewDecoder(r.Body).Decode(&updatedBook); err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if updatedBook.Title == "" || updatedBook.Author == "" {
 http.Error(w, "Title and author are required", http.StatusBadRequest)
 return
 }

 book.Title = updatedBook.Title
 book.Author = updatedBook.Author
 book.Year = updatedBook.Year
 book.ISBN = updatedBook.ISBN

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// Delete a book
func deleteBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 _, exists := books[id]
 if !exists {
 http.Error(w, "Book not found", http.StatusNotFound)
 return
 }

 delete(books, id)

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(Response{Message: "Book deleted successfully"})
}

// Main function to set up the server
func main() {
 r := mux.NewRouter()

 r.HandleFunc("/health", healthHandler).Methods("GET")
 r.HandleFunc("/books", createBook).Methods("POST")
 r.HandleFunc("/books", getBooks).Methods("GET")
 r.HandleFunc("/books/{id}", getBook).Methods("GET")
 r.HandleFunc("/books/{id}", updateBook).Methods("PUT")
 r.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")

 log.Fatal(http.ListenAndServe(":8080", r))
}