package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

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

// In-memory storage for books (in production, use a proper database)
var (
	books = make(map[int]*Book)
 nextID = 1
)

// Health check endpoint
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// Get all books with optional filtering by author
func getAllBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	
	author := r.URL.Query().Get("author")
	var filteredBooks []Book
	for _, book := range books {
		if author == "" || strings.EqualFold(book.Author, author) {
			// Create a copy to avoid returning pointer to internal struct
			b := Book{
				ID:     book.ID,
 Title: book.Title,
 Author: book.Author,
 Year: book.Year,
 ISBN: book.ISBN,
}
			filteredBooks = append(filteredBooks, b)
		}
	}
 json.NewEncoder(w).Encode(filteredBooks)
}

// Get a single book by ID
func getBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 w.WriteHeader(http.StatusBadRequest)
 json.NewEncoder(w).Encode(map[string]string{"error": "Invalid book ID"})
 return
 }

 book, exists := books[id]
 if !exists {
 w.WriteHeader(http.StatusNotFound)
 json.NewEncoder(w).Encode(map[string]string{"error": "Book not found"})
 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// Create a new book
func createBook(w http.ResponseWriter, r *http.Request) {
 var newBook Book
 err := json.NewDecoder(r.Body).Decode(&newBook)
 if err != nil {
 w.WriteHeader(http.StatusBadRequest)
 json.NewEncoder(w).Encode(map[string]string{"error": "Invalid JSON"})
 return
 }

 // Validate required fields
 if newBook.Title == "" || newBook.Author == "" {
 w.WriteHeader(http.StatusBadRequest)
 json.NewEncoder(w).Encode(map[string]string{"error": "Title and author are required"})
 return
 }

 // Create new book with unique ID
 newBook.ID = nextID
 nextID++
 book := &newBook
 books[book.ID] = book

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(book)
}

// Update a book
func updateBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 w.WriteHeader(http.StatusBadRequest)
 json.NewEncoder(w).Encode(map[string]string{"error": "Invalid book ID"})
 return
 }

 book, exists := books[id]
 if !exists {
 w.WriteHeader(http.StatusNotFound)
 json.NewEncoder(w).Encode(map[string]string{"error": "Book not found"})
 return
 }

 var updatedBook Book
 err = json.NewDecoder(r.Body).Decode(&updatedBook)
 if err != nil {
 w.WriteHeader(http.StatusBadRequest)
 json.NewEncoder(w).Encode(map[string]string{"error": "Invalid JSON"})
 return
 }

 // Update book fields
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
 w.WriteHeader(http.StatusBadRequest)
 json.NewEncoder(w).Encode(map[string]string{"error": "Invalid book ID"})
 return
 }

 _, exists := books[id]
 if !exists {
 w.WriteHeader(http.StatusNotFound)
 json.NewEncoder(w).Encode(map[string]string{"error": "Book not found"})
 return
 }

 delete(books, id)
 w.WriteHeader(http.StatusNoContent)
}

func main() {
 // Create router
 r := mux.NewRouter()
 r.HandleFunc("/health", healthHandler).Methods("GET")
 r.HandleFunc("/books", getAllBooks).Methods("GET")
 r.HandleFunc("/books", createBook).Methods("POST")
 r.HandleFunc("/books/{id}", getBook).Methods("GET")
 r.HandleFunc("/books/{id}", updateBook).Methods("PUT")
 r.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")

 fmt.Println("Starting server on :8080...")
 log.Fatal(http.ListenAndServe(":8080", r))
}