package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"github.com/gorilla/mux"
)

// Book represents a book in the collection
type Book struct {
	ID      int    `json:"id"`
	Title   string `json:"title"`
	Author  string `json:"author"`
	Year    int    `json:"year"`
	ISBN    string `json:"isbn"`
}

// In-memory storage for books (in production, this would be a database)
var (
	books   = make(map[int]Book)
	nextID  = 1
)

// Response represents a response structure
type Response struct {
	Message string `json:"message"`
}

// HealthCheck handler
func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// getAllBooks returns all books, optionally filtered by author
func getAllBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	
	author := r.URL.Query().Get("author")
	booksList := []Book{}

	// If author filter is provided, filter by author
	for _, book := range books {
		if strings.EqualFold(book.Author, author) {
			booksList = append(booksList, book)
		}
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(booksList)
}

// getBookByID returns a single book by ID
func getBookByID(w http.ResponseWriter, r *http.Request) {
	// Get the ID from URL parameter
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusBadRequest)
	 json.NewEncoder(w).Encode(Response{Message: "Invalid book ID"})
	 return
 }

 book, exists := books[id]
 if !exists {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusNotFound)
	 json.NewEncoder(w).Encode(Response{Message: "Book not found"})
	 return
 }

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(book)
}

// createBook creates a new book
func createBook(w http.ResponseWriter, r *http.Request) {
	var newBook Book
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&newBook); err != nil {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusBadRequest)
	 json.NewEncoder(w).Encode(Response{Message: "Invalid JSON"})
	 return
 }

 // Validate required fields
 if newBook.Title == "" {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusBadRequest)
	 json.NewEncoder(w).Encode(Response{Message: "Title is required"})
	 return
 }

 if newBook.Author == "" {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusBadRequest)
	 json.NewEncoder(w).Encode(Response{Message: "Author is required"})
	 return
 }

 // Create new book with unique ID
 newBook.ID = nextID
 books[nextID] = newBook
 nextID++

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(newBook)
}

// updateBook updates an existing book
func updateBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusBadRequest)
	 json.NewEncoder(w).Encode(Response{Message: "Invalid book ID"})
	 return
 }

 book, exists := books[id]
 if !exists {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusNotFound)
	 json.NewEncoder(w).Encode(Response{Message: "Book not found"})
	 return
 }

 var updatedBook Book
 decoder := json.NewDecoder(r.Body)
 if err := decoder.Decode(&updatedBook); err != nil {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusBadRequest)
	 json.NewEncoder(w).Encode(Response{Message: "Invalid JSON"})
	 return
 }

 // If title or author is empty, keep existing values
 if updatedBook.Title == "" {
	 updatedBook.Title = book.Title
 }

 if updatedBook.Author == "" {
	 updatedBook.Author = book.Author
 }

 updatedBook.ID = book.ID
 books[id] = updatedBook

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(updatedBook)
}

// deleteBook deletes a book by ID
func deleteBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusBadRequest)
	 json.NewEncoder(w).Encode(Response{Message: "Invalid book ID"})
	 return
 }

 _, exists := books[id]
 if !exists {
	 w.Header().Set("Content-Type", "application/json")
	 w.WriteHeader(http.StatusNotFound)
	 json.NewEncoder(w).Encode(Response{Message: "Book not found"})
	 return
 }

 delete(books, id)

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(Response{Message: "Book deleted"})
}

func main() {
 // Create router
 router := mux.NewRouter()

 // Define routes
 router.HandleFunc("/health", healthCheck).Methods("GET")
 router.HandleFunc("/books", createBook).Methods("POST")
 router.HandleFunc("/books", getAllBooks).Methods("GET")
 router.HandleFunc("/books/{id}", getBookByID).Methods("GET")
 router.HandleFunc("/books/{id}", updateBook).Methods("PUT")
 router.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")

 // Start server
 fmt.Println("Book API server running on port 8080")
 fmt.Println("Health check endpoint: GET /health")
 fmt.Println("Create book: POST /books")
 fmt.Println("Get all books: GET /books")
 fmt.Println("Get book by ID: GET /books/{id}")
 fmt.Println("Update book: PUT /books/{id}")
 fmt.Println("Delete book: DELETE /books/{id}")
 fmt.Println("")

 // Start server
 fmt.Println("Starting server on port 8080...")
 http.ListenAndServe(":8080", router)
}