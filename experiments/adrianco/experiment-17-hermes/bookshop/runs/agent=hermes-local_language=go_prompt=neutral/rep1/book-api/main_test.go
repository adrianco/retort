package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthCheck(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Errorf("Failed to unmarshal JSON response: %v", err)
	}

	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	// Create a book
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
	createBook(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status code %d, got %d", http.StatusCreated, w.Code)
	}

	// Parse response to get the created book ID
	var createdBook Book
	if err := json.Unmarshal(w.Body.Bytes(), &createdBook); err != nil {
		t.Errorf("Failed to unmarshal JSON response: %v", err)
	}

	// Get the book by ID
	req = httptest.NewRequest("GET", "/books/"+string(rune(createdBook.ID)), nil)
	w = httptest.NewRecorder()
	getBook(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}
}

func TestListBooks(t *testing.T) {
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	listBooks(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}
}

func TestCreateBookWithMissingFields(t *testing.T) {
	// Create a book with missing required fields
	bookData := map[string]interface{}{
		"title": "Test Book",
		// Missing author
		"year": 2023,
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBook(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", http.StatusBadRequest, w.Code)
	}
}
