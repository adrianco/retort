package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

// TestHealthCheck tests the health check endpoint
func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Errorf("Failed to unmarshal response: %v", err)
	}

	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response["status"])
	}
}

// TestCreateBook tests creating a new book
func TestCreateBook(t *testing.T) {
	// Initialize database
	initDB()
	defer db.Close()

	// Create a test book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	// Marshal to JSON
	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	// Create request
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	// Create response recorder
	w := httptest.NewRecorder()

	// Call handler
	createBookHandler(w, req)

	// Check status code
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status code %d, got %d", http.StatusCreated, w.Code)
	}

	// Check response
	var response Book
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Errorf("Failed to unmarshal response: %v", err)
	}

	// Verify fields
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
		t.Errorf("Expected ISBN '%s', got '%s'", book.ISBN, response.ISBN)
	}
	if response.ID <= 0 {
		t.Errorf("Expected valid ID, got %d", response.ID)
	}
}

// TestCreateBookWithInvalidData tests creating a book with invalid data
func TestCreateBookWithInvalidData(t *testing.T) {
	// Initialize database
	initDB()
	defer db.Close()

	// Create a test book with missing required fields
	book := Book{
		Title:  "",
		Author: "",
		Year:   2023,
		ISBN:   "1234567890",
	}

	// Marshal to JSON
	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	// Create request
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	// Create response recorder
	w := httptest.NewRecorder()

	// Call handler
	createBookHandler(w, req)

	// Check status code
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", http.StatusBadRequest, w.Code)
	}
}

// TestGetBooks tests retrieving all books
func TestGetBooks(t *testing.T) {
	// Initialize database
	initDB()
	defer db.Close()

	// Create a test book first
	book := Book{
		Title:  "Test Book 2",
		Author: "Test Author 2",
		Year:   2022,
		ISBN:   "0987654321",
	}

	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}

	// Now test getting all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	getBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response []Book
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Errorf("Failed to unmarshal response: %v", err)
	}

	if len(response) == 0 {
		t.Error("Expected at least one book in response")
	}
}

// TestGetBookById tests retrieving a single book by ID
func TestGetBookById(t *testing.T) {
	// Initialize database
	initDB()
	defer db.Close()

	// Create a test book first
	book := Book{
		Title:  "Test Book 3",
		Author: "Test Author 3",
		Year:   2021,
		ISBN:   "1122334455",
	}

	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}

	// Extract the ID from the created book
	var createdBook Book
	if err := json.Unmarshal(w.Body.Bytes(), &createdBook); err != nil {
		t.Fatalf("Failed to unmarshal created book: %v", err)
	}

	// Test getting the book by ID
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response Book
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Errorf("Failed to unmarshal response: %v", err)
	}

	if response.ID != createdBook.ID {
		t.Errorf("Expected ID %d, got %d", createdBook.ID, response.ID)
	}
	if response.Title != book.Title {
		t.Errorf("Expected title '%s', got '%s'", book.Title, response.Title)
	}
	if response.Author != book.Author {
		t.Errorf("Expected author '%s', got '%s'", book.Author, response.Author)
	}
}

// TestUpdateBook tests updating a book
func TestUpdateBook(t *testing.T) {
	// Initialize database
	initDB()
	defer db.Close()

	// Create a test book first
	book := Book{
		Title:  "Test Book 4",
		Author: "Test Author 4",
		Year:   2020,
		ISBN:   "5566778899",
	}

	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}

	// Extract the ID from the created book
	var createdBook Book
	if err := json.Unmarshal(w.Body.Bytes(), &createdBook); err != nil {
		t.Fatalf("Failed to unmarshal created book: %v", err)
	}

	// Update the book
	updatedBook := Book{
		Title:  "Updated Test Book",
		Author: "Updated Test Author",
		Year:   2024,
		ISBN:   "9988776655",
	}

	jsonData, err = json.Marshal(updatedBook)
	if err != nil {
		t.Fatalf("Failed to marshal updated book: %v", err)
	}

	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	updateBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response Book
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Errorf("Failed to unmarshal response: %v", err)
	}

	if response.ID != createdBook.ID {
		t.Errorf("Expected ID %d, got %d", createdBook.ID, response.ID)
	}
	if response.Title != updatedBook.Title {
		t.Errorf("Expected title '%s', got '%s'", updatedBook.Title, response.Title)
	}
	if response.Author != updatedBook.Author {
		t.Errorf("Expected author '%s', got '%s'", updatedBook.Author, response.Author)
	}
	if response.Year != updatedBook.Year {
		t.Errorf("Expected year %d, got %d", updatedBook.Year, response.Year)
	}
	if response.ISBN != updatedBook.ISBN {
		t.Errorf("Expected ISBN '%s', got '%s'", updatedBook.ISBN, response.ISBN)
	}
}

// TestDeleteBook tests deleting a book
func TestDeleteBook(t *testing.T) {
	// Initialize database
	initDB()
	defer db.Close()

	// Create a test book first
	book := Book{
		Title:  "Test Book 5",
		Author: "Test Author 5",
		Year:   2019,
		ISBN:   "1234567890",
	}

	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("Failed to create test book: %d", w.Code)
	}

	// Extract the ID from the created book
	var createdBook Book
	if err := json.Unmarshal(w.Body.Bytes(), &createdBook); err != nil {
		t.Fatalf("Failed to unmarshal created book: %v", err)
	}

	// Delete the book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	deleteBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	// Verify deletion by trying to get it
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status code %d (NotFound), got %d", http.StatusNotFound, w.Code)
	}
}