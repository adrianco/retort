package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestBookAPI(t *testing.T) {
	// Create a temporary database for testing
	store, err := NewBookStore(":memory:")
	if err != nil {
		t.Fatal("Failed to create database:", err)
	}
	defer store.Close()

	// Test creating a book
	book := Book{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	bookJSON, err := json.Marshal(book)
	if err != nil {
		t.Fatal("Failed to marshal book:", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(bookJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	// Create a handler function that wraps our main handler for testing
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/books":
			switch r.Method {
			case "POST":
				handleCreateBook(w, r, store)
			case "GET":
				handleGetBooks(w, r, store)
			}
		case "/books/1":
			switch r.Method {
			case "GET":
				handleGetBook(w, r, store, 1)
			case "PUT":
				handleUpdateBook(w, r, store, 1)
			case "DELETE":
				handleDeleteBook(w, r, store, 1)
			}
		case "/health":
			handleHealth(w, r, store)
		}
	})

	handler.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}

	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Fatal("Failed to unmarshal response:", err)
	}
	if createdBook.Title != book.Title {
		t.Errorf("Expected title %s, got %s", book.Title, createdBook.Title)
	}
	if createdBook.Author != book.Author {
		t.Errorf("Expected author %s, got %s", book.Author, createdBook.Author)
	}
	if createdBook.Year != book.Year {
		t.Errorf("Expected year %d, got %d", book.Year, createdBook.Year)
	}
	if createdBook.ISBN != book.ISBN {
		t.Errorf("Expected ISBN %s, got %s", book.ISBN, createdBook.ISBN)
	}
	if createdBook.ID != 1 {
		t.Errorf("Expected ID 1, got %d", createdBook.ID)
	}

	// Test getting all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	err = json.Unmarshal(w.Body.Bytes(), &books)
	if err != nil {
		t.Fatal("Failed to unmarshal response:", err)
	}
	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}
	if books[0].Title != book.Title {
		t.Errorf("Expected title %s, got %s", book.Title, books[0].Title)
	}

	// Test getting a single book
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var retrievedBook Book
	err = json.Unmarshal(w.Body.Bytes(), &retrievedBook)
	if err != nil {
		t.Fatal("Failed to unmarshal response:", err)
	}
	if retrievedBook.Title != book.Title {
		t.Errorf("Expected title %s, got %s", book.Title, retrievedBook.Title)
	}
	if retrievedBook.Author != book.Author {
		t.Errorf("Expected author %s, got %s", book.Author, retrievedBook.Author)
	}
	if retrievedBook.Year != book.Year {
		t.Errorf("Expected year %d, got %d", book.Year, retrievedBook.Year)
	}
	if retrievedBook.ISBN != book.ISBN {
		t.Errorf("Expected ISBN %s, got %s", book.ISBN, retrievedBook.ISBN)
	}
	if retrievedBook.ID != 1 {
		t.Errorf("Expected ID 1, got %d", retrievedBook.ID)
	}

	// Test updating a book
	updatedBook := Book{
		Title:  "The Go Programming Language (2nd Edition)",
		Author: "Alan A. A. Donovan & Brian W. Kernighan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	updatedBookJSON, err := json.Marshal(updatedBook)
	if err != nil {
		t.Fatal("Failed to marshal updated book:", err)
	}

	req = httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(updatedBookJSON))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var updatedBookResult Book
	err = json.Unmarshal(w.Body.Bytes(), &updatedBookResult)
	if err != nil {
		t.Fatal("Failed to unmarshal response:", err)
	}
	if updatedBookResult.Title != updatedBook.Title {
		t.Errorf("Expected title %s, got %s", updatedBook.Title, updatedBookResult.Title)
	}
	if updatedBookResult.Author != updatedBook.Author {
		t.Errorf("Expected author %s, got %s", updatedBook.Author, updatedBookResult.Author)
	}
	if updatedBookResult.Year != updatedBook.Year {
		t.Errorf("Expected year %d, got %d", updatedBook.Year, updatedBookResult.Year)
	}
	if updatedBookResult.ISBN != updatedBook.ISBN {
		t.Errorf("Expected ISBN %s, got %s", updatedBook.ISBN, updatedBookResult.ISBN)
	}

	// Test deleting a book
	req = httptest.NewRequest("DELETE", "/books/1", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d", http.StatusNoContent, w.Code)
	}

	// Verify book was deleted
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestBookAPIValidation(t *testing.T) {
	// Create a temporary database for testing
	store, err := NewBookStore(":memory:")
	if err != nil {
		t.Fatal("Failed to create database:", err)
	}
	defer store.Close()

	// Test creating a book without required fields
	book := Book{
		Title:  "",
		Author: "",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	bookJSON, err := json.Marshal(book)
	if err != nil {
		t.Fatal("Failed to marshal book:", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(bookJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	// Create a handler function that wraps our main handler for testing
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/books":
			switch r.Method {
			case "POST":
				handleCreateBook(w, r, store)
			}
		}
	})

	handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
	if !strings.Contains(w.Body.String(), "Title and author are required") {
		t.Errorf("Expected error message not found in response: %s", w.Body.String())
	}

	// Test creating a book with invalid JSON
	req = httptest.NewRequest("POST", "/books", strings.NewReader("{invalid json"))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
	if !strings.Contains(w.Body.String(), "Invalid JSON") {
		t.Errorf("Expected error message not found in response: %s", w.Body.String())
	}
}

func TestBookAPIFiltering(t *testing.T) {
	// Create a temporary database for testing
	store, err := NewBookStore(":memory:")
	if err != nil {
		t.Fatal("Failed to create database:", err)
	}
	defer store.Close()

	// Create test books
	book1 := Book{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	book2 := Book{
		Title:  "The Go Programming Language",
		Author: "Brian W. Kernighan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	// Create first book
	book1JSON, err := json.Marshal(book1)
	if err != nil {
		t.Fatal("Failed to marshal book:", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(book1JSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/books":
			switch r.Method {
			case "POST":
				handleCreateBook(w, r, store)
			case "GET":
				handleGetBooks(w, r, store)
			}
		}
	})

	handler.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}

	// Create second book
	book2JSON, err := json.Marshal(book2)
	if err != nil {
		t.Fatal("Failed to marshal book:", err)
	}

	req = httptest.NewRequest("POST", "/books", bytes.NewBuffer(book2JSON))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}

	// Test filtering by author
	req = httptest.NewRequest("GET", "/books?author=Donovan", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	err = json.Unmarshal(w.Body.Bytes(), &books)
	if err != nil {
		t.Fatal("Failed to unmarshal response:", err)
	}
	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}
	if books[0].Title != book1.Title {
		t.Errorf("Expected title %s, got %s", book1.Title, books[0].Title)
	}

	// Test filtering by author (non-existent)
	req = httptest.NewRequest("GET", "/books?author=NonExistent", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	err = json.Unmarshal(w.Body.Bytes(), &books)
	if err != nil {
		t.Fatal("Failed to unmarshal response:", err)
	}
	if len(books) != 0 {
		t.Errorf("Expected 0 books, got %d", len(books))
	}
}

func handleHealth(w http.ResponseWriter, r *http.Request, store *BookStore) {
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	err := store.HealthCheck()
	if err != nil {
		http.Error(w, "Service unhealthy", http.StatusServiceUnavailable)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}