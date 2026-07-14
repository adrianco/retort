package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"strings"
	"testing"

	"github.com/gorilla/mux"
)

func TestMain(m *testing.M) {
	// Initialize database
	initDB()
	
	// Run tests
	code := m.Run()
	
	// Clean up
	closeDB()
	os.Remove("./books.db")
	
	os.Exit(code)
}

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	
	router := mux.NewRouter()
	router.HandleFunc("/health", healthCheck).Methods("GET")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	
	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	// Test valid book creation
	book := Book{
		Title:  "1984",
		Author: "George Orwell",
		Year:   1948,
		ISBN:   "978-0451524935",
	}
	
	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	router := mux.NewRouter()
	router.HandleFunc("/books", createBook).Methods("POST")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}
	
	var response Book
	err = json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if response.Title != book.Title {
		t.Errorf("Expected title '%s', got '%s'", book.Title, response.Title)
	}
	
	if response.Author != book.Author {
		t.Errorf("Expected author '%s', got '%s'", book.Author, response.Author)
	}
	
	if response.Year != book.Year {
		t.Errorf("Expected year %d, got %d", book.Year, response.Year)
	}
	
	if response.ISBN != book.ISBN {
		t.Errorf("Expected isbn '%s', got '%s'", book.ISBN, response.ISBN)
	}
}

func TestGetBooks(t *testing.T) {
	// First create a book
	book := Book{
		Title:  "To Kill a Mockingbird",
		Author: "Harper Lee",
		Year:   1960,
		ISBN:   "978-0061120084",
	}
	
	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	router := mux.NewRouter()
	router.HandleFunc("/books", createBook).Methods("POST")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}
	
	// Now test getting all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	
	router.HandleFunc("/books", getBooks).Methods("GET")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	
	var response []Book
	err = json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if len(response) == 0 {
		t.Error("Expected at least one book in the response")
	}
}

func TestGetBookById(t *testing.T) {
	// First create a book
	book := Book{
		Title:  "Brave New World",
		Author: "Aldous Huxley",
		Year:   1932,
		ISBN:   "978-0064400548",
	}
	
	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	router := mux.NewRouter()
	router.HandleFunc("/books", createBook).Methods("POST")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}
	
	// Extract the ID from the created book
	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Fatalf("Failed to unmarshal created book: %v", err)
	}
	
	// Now test getting book by ID
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	
	router.HandleFunc("/books/{id}", getBook).Methods("GET")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	
	var response Book
	err = json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if response.ID != createdBook.ID {
		t.Errorf("Expected ID %d, got %d", createdBook.ID, response.ID)
	}
	
	if response.Title != book.Title {
		t.Errorf("Expected title '%s', got '%s'", book.Title, response.Title)
	}
}

func TestUpdateBook(t *testing.T) {
	// First create a book
	book := Book{
		Title:  "Animal Farm",
		Author: "George Orwell",
		Year:   1945,
		ISBN:   "978-0453050877",
	}
	
	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	router := mux.NewRouter()
	router.HandleFunc("/books", createBook).Methods("POST")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}
	
	// Extract the ID from the created book
	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Fatalf("Failed to unmarshal created book: %v", err)
	}
	
	// Update the book
	updatedBook := Book{
		Title:  "Animal Farm (Updated)",
		Author: "George Orwell",
		Year:   1945,
		ISBN:   "978-0453050877",
	}
	
	jsonData, err = json.Marshal(updatedBook)
	if err != nil {
		t.Fatalf("Failed to marshal updated book: %v", err)
	}
	
	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	
	router.HandleFunc("/books/{id}", updateBook).Methods("PUT")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	
	var response Book
	err = json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if response.Title != updatedBook.Title {
		t.Errorf("Expected title '%s', got '%s'", updatedBook.Title, response.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	// First create a book
	book := Book{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}
	
	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	router := mux.NewRouter()
	router.HandleFunc("/books", createBook).Methods("POST")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}
	
	// Extract the ID from the created book
	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Fatalf("Failed to unmarshal created book: %v", err)
	}
	
	// Now delete the book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	
	router.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status 204, got %d", w.Code)
	}
	
	// Try to get the deleted book (should return 404)
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	
	router.HandleFunc("/books/{id}", getBook).Methods("GET")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 after deletion, got %d", w.Code)
	}
}

func TestGetBooksWithFilter(t *testing.T) {
	// First create some books
	books := []Book{
		{
			Title:  "Book A",
			Author: "Author X",
			Year:   2000,
			ISBN:   "123",
		},
		{
			Title:  "Book B",
			Author: "Author Y",
			Year:   2001,
			ISBN:   "456",
		},
		{
			Title:  "Book C",
			Author: "Author X",
			Year:   2002,
			ISBN:   "789",
		},
	}
	
	for _, book := range books {
		jsonData, err := json.Marshal(book)
		if err != nil {
			t.Fatalf("Failed to marshal book: %v", err)
		}
		
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		
		router := mux.NewRouter()
		router.HandleFunc("/books", createBook).Methods("POST")
		router.ServeHTTP(w, req)
		
		if w.Code != http.StatusCreated {
			t.Fatalf("Failed to create test book: %d", w.Code)
		}
	}
	
	// Test filtering by author
	req := httptest.NewRequest("GET", "/books?author=Author%20X", nil)
	w := httptest.NewRecorder()
	
	router := mux.NewRouter()
	router.HandleFunc("/books", getBooks).Methods("GET")
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	
	var response []Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	// Should return 2 books with Author X
	if len(response) != 2 {
		t.Errorf("Expected 2 books with Author X, got %d", len(response))
	}
	
	for _, book := range response {
		if !strings.Contains(strings.ToLower(book.Author), "author x") {
			t.Errorf("Book author '%s' doesn't match filter 'Author X'", book.Author)
		}
	}
}