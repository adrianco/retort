package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"
)

func TestMain(m *testing.M) {
	// Initialize database before tests
	initDB()
	
	// Run tests
	code := m.Run()
	
	// Clean up
	os.Remove("./books.db")
	
	os.Exit(code)
}

func TestHealthHandler(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var response map[string]string
	json.Unmarshal(w.Body.Bytes(), &response)
	
	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	// Test valid book creation
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}
	
	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	if response.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", response.Title)
	}
	
	if response.Author != "Test Author" {
		t.Errorf("Expected author 'Test Author', got '%s'", response.Author)
	}
}

func TestCreateBookMissingFields(t *testing.T) {
	// Test book creation with missing required fields
	bookData := map[string]interface{}{
		"title": "Test Book",
		"year":  2023,
	}
	
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestGetBooks(t *testing.T) {
	// First create a book
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	// Now test getting all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	booksHandler(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var response []Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	if len(response) == 0 {
		t.Error("Expected at least one book")
	}
}

func TestGetBook(t *testing.T) {
	// First create a book
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	// Extract the ID from the created book
	var createdBook Book
	json.Unmarshal(w.Body.Bytes(), &createdBook)
	
	// Test getting the specific book
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	if response.ID != createdBook.ID {
		t.Errorf("Expected ID %d, got %d", createdBook.ID, response.ID)
	}
}

func TestUpdateBook(t *testing.T) {
	// First create a book
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	// Extract the ID from the created book
	var createdBook Book
	json.Unmarshal(w.Body.Bytes(), &createdBook)
	
	// Update the book
	updateData := map[string]interface{}{
		"title":  "Updated Test Book",
		"author": "Updated Test Author",
		"year":   2024,
		"isbn":   "0987654321",
	}
	
	jsonData, _ = json.Marshal(updateData)
	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w = httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	if response.Title != "Updated Test Book" {
		t.Errorf("Expected title 'Updated Test Book', got '%s'", response.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	// First create a book
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "1234567890",
	}
	
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	// Extract the ID from the created book
	var createdBook Book
	json.Unmarshal(w.Body.Bytes(), &createdBook)
	
	// Delete the book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	// Try to get the deleted book
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestGetBookNotFound(t *testing.T) {
	// Try to get a book that doesn't exist
	req := httptest.NewRequest("GET", "/books/999", nil)
	w := httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	// Try to update a book that doesn't exist
	updateData := map[string]interface{}{
		"title":  "Updated Test Book",
		"author": "Updated Test Author",
		"year":   2024,
		"isbn":   "0987654321",
	}
	
	jsonData, _ := json.Marshal(updateData)
	req := httptest.NewRequest("PUT", "/books/999", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	// Try to delete a book that doesn't exist
	req := httptest.NewRequest("DELETE", "/books/999", nil)
	w := httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestCreateBookInvalidJSON(t *testing.T) {
	// Test book creation with invalid JSON
	req := httptest.NewRequest("POST", "/books", bytes.NewBufferString("{invalid json}"))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestBooksHandlerMethodNotAllowed(t *testing.T) {
	// Try a method that's not allowed on /books
	req := httptest.NewRequest("PATCH", "/books", nil)
	w := httptest.NewRecorder()
	booksHandler(w, req)
	
	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("Expected status %d, got %d", http.StatusMethodNotAllowed, w.Code)
	}
}

func TestBookHandlerMethodNotAllowed(t *testing.T) {
	// Try a method that's not allowed on /books/{id}
	req := httptest.NewRequest("PATCH", "/books/1", nil)
	w := httptest.NewRecorder()
	bookHandler(w, req)
	
	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("Expected status %d, got %d", http.StatusMethodNotAllowed, w.Code)
	}
}