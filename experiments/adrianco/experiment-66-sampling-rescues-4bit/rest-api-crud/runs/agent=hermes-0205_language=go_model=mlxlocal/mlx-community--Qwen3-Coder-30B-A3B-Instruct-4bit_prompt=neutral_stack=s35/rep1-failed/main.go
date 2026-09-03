package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
)

// Book represents a book with its details
type Book struct {
	ID      int `json:"id"`
	Title   string `json:"title"`
	Author  string `json:"author"`
	Year    int `json:"year"`
	ISBN    string `json:"isbn"`
}

// In-memory storage for books
var (
	books []Book
)

func init() {
	// Initialize with some sample data
	books = append(books, Book{ID: 1, Title: "The Great Gatsby", Author: "F. Scott Fitzgerald", Year: 1925, ISBN: "9780743273502"})
	books = append(books, Book{ID: 2, Title: "To Kill a Mockingbird", Author: "Harper Lee", Year: 1960, ISBN: "9780061120084"})
	books = append(books, Book{ID: 3, Title: "1984", Author: "George Orwell", Year: 1948, ISBN: "9780452055340"})
}

func main() {
	// Create router
	r := mux.NewRouter()

	// Define routes
	r.HandleFunc("/health", healthCheck).Methods("GET")
	r.HandleFunc("/books", getBooks).Methods("GET")
	r.HandleFunc("/books", createBook).Methods("POST")
	r.HandleFunc("/books/{id}", getBook).Methods("GET")
	r.HandleFunc("/books/{id}", updateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")

	// Start server
	fmt.Println("Server starting on port 8080...")
	log.Fatal(http.ListenAndServe(":8080", r))
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func getBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	author := r.URL.Query().Get("author")
	if author != "" {
		// Filter books by author
		filteredBooks := []Book{}
		for _, book := range books {
		 if book.Author == author {
 filteredBooks = append(filteredBooks, book)
 }
 }
 json.NewEncoder(w).Encode(filteredBooks)
 } else {
 json.NewEncoder(w).Encode(books)
 }
}

func getBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 for _, book := range books {
 if book.ID == id {
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
 return
 }
 }

 http.Error(w, "Book not found", http.StatusNotFound)
}

func createBook(w http.ResponseWriter, r *http.Request) {
 var newBook Book
 err := json.NewDecoder(r.Body).Decode(&newBook)
 if err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Validate required fields
 if newBook.Title == "" {
 http.Error(w, "Title is required", http.StatusBadRequest)
 return
 }

 if newBook.Author == "" {
 http.Error(w, "Author is required", http.StatusBadRequest)
 return
 }

 newBook.ID = len(books) + 1
 books = append(books, newBook)

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(newBook)
}

func updateBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 var updatedBook Book
 err = json.NewDecoder(r.Body).Decode(&updatedBook)
 if err != nil {
 http.Error(w, "Invalid JSON", http.StatusBadRequest)
 return
 }

 // Find and update the book
 for i, book := range books {
 if book.ID == id {
 updatedBook.ID = id
 books[i] = updatedBook
 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(updatedBook)
 return
 }
 }

 http.Error(w, "Book not found", http.StatusNotFound)
}

func deleteBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
 http.Error(w, "Invalid book ID", http.StatusBadRequest)
 return
 }

 // Find and remove the book
 newBooks := []Book{}
 for _, book := range books {
 if book.ID != id {
 newBooks = append(newBooks, book)
 }
 }
 books = newBooks
 w.WriteHeader(http.StatusNoContent)
}