package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

// Test helpers
func createTestBook(t *testing.T, title, author string) *Book {
	body := map[string]interface{}{
		"title":  title,
		"author": author,
		"year":   2023,
		"isbn":   "123-456-789",
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("Failed to marshal JSON: %v", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("Expected status 201, got %d", w.Code)
	}

	var book Book
	err = json.Unmarshal(w.Body.Bytes(), &book)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	return &book
}

func getTestBook(t *testing.T, id int) *Book {
	req := httptest.NewRequest("GET", fmt.Sprintf("/books/%d", id), nil)
	w := httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d", w.Code)
	}

	var book Book
	err := json.Unmarshal(w.Body.Bytes(), &book)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	return &book
}

func updateTestBook(t *testing.T, id int, title, author string) *Book {
	body := map[string]interface{}{
		"title":  title,
		"author": author,
		"year":   2024,
		"isbn":   "987-654-321",
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("Failed to marshal JSON: %v", err)
	}

	req := httptest.NewRequest("PUT", fmt.Sprintf("/books/%d", id), bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	updateBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d", w.Code)
	}

	var book Book
	err = json.Unmarshal(w.Body.Bytes(), &book)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	return &book
}

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d", w.Code)
	}

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	if response["status"] != "healthy" {
		t.Fatalf("Expected status 'healthy', got '%s'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	// Create a book
	book := createTestBook(t, "Test Book", "Test Author")
	
	// Verify the book was created with the correct fields
	if book.Title != "Test Book" {
		t.Fatalf("Expected title 'Test Book', got '%s'", book.Title)
	}
	
	if book.Author != "Test Author" {
		t.Fatalf("Expected author 'Test Author', got '%s'", book.Author)
	}
	
	if book.Year != 2023 {
		t.Fatalf("Expected year 2023, got %d", book.Year)
	}
	
	if book.ISBN != "123-456-789" {
		t.Fatalf("Expected ISBN '123-456-789', got '%s'", book.ISBN)
	}
	
	// Verify book has an ID
	if book.ID <= 0 {
		t.Fatalf("Expected a positive ID, got %d", book.ID)
	}
}

func TestGetAllBooks(t *testing.T) {
	// Create a few test books
	book1 := createTestBook(t, "Book 1", "Author 1")
	book2 := createTestBook(t, "Book 2", "Author 2")
	
	// Get all books
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	getBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	err := json.Unmarshal(w.Body.Bytes(), &books)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	// Should have at least 2 books
	if len(books) < 2 {
		t.Fatalf("Expected at least 2 books, got %d", len(books))
	}

	// Find our test books
	foundBook1 := false
	foundBook2 := false
	
	for _, book := range books {
		if book.ID == book1.ID && book.Title == "Book 1" {
			foundBook1 = true
		}
		if book.ID == book2.ID && book.Title == "Book 2" {
			foundBook2 = true
		}
	}

	if !foundBook1 {
		t.Fatalf("Did not find book 1")
	}
	
	if !foundBook2 {
		t.Fatalf("Did not find book 2")
	}
}

func TestGetBookById(t *testing.T) {
	// Create a book
	book := createTestBook(t, "Book by ID", "Author by ID")
	
	// Get the book by ID
	req := httptest.NewRequest("GET", fmt.Sprintf("/books/%d", book.ID), nil)
	w := httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d", w.Code)
	}

	var retrievedBook Book
	err := json.Unmarshal(w.Body.Bytes(), &retrievedBook)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	// Verify it's the same book
	if retrievedBook.ID != book.ID {
		t.Fatalf("Expected ID %d, got %d", book.ID, retrievedBook.ID)
	}
	
	if retrievedBook.Title != "Book by ID" {
		t.Fatalf("Expected title 'Book by ID', got '%s'", retrievedBook.Title)
	}
	
	if retrievedBook.Author != "Author by ID" {
		t.Fatalf("Expected author 'Author by ID', got '%s'", retrievedBook.Author)
	}
}

func TestUpdateBook(t *testing.T) {
	// Create a book
	book := createTestBook(t, "Original Title", "Original Author")
	
	// Update the book
	updatedBook := updateTestBook(t, book.ID, "Updated Title", "Updated Author")
	
	// Verify the update
	if updatedBook.Title != "Updated Title" {
		t.Fatalf("Expected title 'Updated Title', got '%s'", updatedBook.Title)
	}
	
	if updatedBook.Author != "Updated Author" {
		t.Fatalf("Expected author 'Updated Author', got '%s'", updatedBook.Author)
	}
	
	if updatedBook.Year != 2024 {
		t.Fatalf("Expected year 2024, got %d", updatedBook.Year)
	}
	
	if updatedBook.ISBN != "987-654-321" {
		t.Fatalf("Expected ISBN '987-654-321', got '%s'", updatedBook.ISBN)
	}
}

func TestDeleteBook(t *testing.T) {
	// Create a book
	book := createTestBook(t, "Book to Delete", "Author of Deleted Book")
	
	// Delete the book
	req := httptest.NewRequest("DELETE", fmt.Sprintf("/books/%d", book.ID), nil)
	w := httptest.NewRecorder()
	deleteBookHandler(w, req)

	if w.Code != http.StatusNoContent {
		t.Fatalf("Expected status 204, got %d", w.Code)
	}

	// Try to get the deleted book - should return 404
	req = httptest.NewRequest("GET", fmt.Sprintf("/books/%d", book.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("Expected status 404, got %d", w.Code)
	}
}

func TestGetBooksByAuthorFilter(t *testing.T) {
	// Create books with different authors
	book1 := createTestBook(t, "Book 1", "Author A")
	book2 := createTestBook(t, "Book 2", "Author A")
	
	// Get books by author "Author A"
	req := httptest.NewRequest("GET", "/books?author=Author%20A", nil)
	w := httptest.NewRecorder()
	getBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	err := json.Unmarshal(w.Body.Bytes(), &books)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	// Should have exactly 2 books (both by Author A)
	if len(books) != 2 {
		t.Fatalf("Expected 2 books by Author A, got %d", len(books))
	}

	// Verify all books are by Author A
	for _, book := range books {
		if book.Author != "Author A" {
			t.Fatalf("Expected all books to be by Author A, got one by %s", book.Author)
		}
	}
	
	// Verify we got the correct books by ID
	foundBook1 := false
	foundBook2 := false
	
	for _, book := range books {
		if book.ID == book1.ID {
			foundBook1 = true
		}
		if book.ID == book2.ID {
			foundBook2 = true
		}
	}

	if !foundBook1 || !foundBook2 {
		t.Fatalf("Did not find all books with Author A")
	}
}

func TestCreateBookValidation(t *testing.T) {
	// Try to create a book without required fields
	body := map[string]interface{}{
		"title":  "",
		"author": "",
		"year":   2023,
		"isbn":   "123-456-789",
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("Failed to marshal JSON: %v", err)
	}

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("Expected status 400, got %d", w.Code)
	}
}

func TestGetNonExistentBook(t *testing.T) {
	req := httptest.NewRequest("GET", "/books/999999", nil)
	w := httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("Expected status 404, got %d", w.Code)
	}
}

func TestUpdateNonExistentBook(t *testing.T) {
	body := map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
		"year":   2024,
		"isbn":   "987-654-321",
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("Failed to marshal JSON: %v", err)
	}

	req := httptest.NewRequest("PUT", "/books/999999", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	updateBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("Expected status 404, got %d", w.Code)
	}
}

func TestDeleteNonExistentBook(t *testing.T) {
	req := httptest.NewRequest("DELETE", "/books/999999", nil)
	w := httptest.NewRecorder()
	deleteBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("Expected status 404, got %d", w.Code)
	}
}

func TestMain(m *testing.M) {
	// Initialize database before running tests
	initDB()
	
	// Run tests
	code := m.Run()
	
	// Clean up
	os.Remove("./books.db")
	
	os.Exit(code)
}