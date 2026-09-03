package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestMain(m *testing.M) {
	// Initialize database
	initDB()

	// Run tests
	code := m.Run()

	// Clean up
	os.Exit(code)
}

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Errorf("Error unmarshaling JSON: %v", err)
	}

	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	// Test valid book creation
	bookData := map[string]interface{}{
		"title":  "1984",
		"author": "George Orwell",
		"year":   1948,
		"isbn":   "978-0-452-28423-4",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Errorf("Error unmarshaling JSON: %v", err)
	}

	if response.Title != "1984" {
		t.Errorf("Expected title '1984', got '%s'", response.Title)
	}

	if response.Author != "George Orwell" {
		t.Errorf("Expected author 'George Orwell', got '%s'", response.Author)
	}

	if response.Year != 1948 {
		t.Errorf("Expected year 1948, got %d", response.Year)
	}

	if response.ISBN != "978-0-452-28423-4" {
		t.Errorf("Expected ISBN '978-0-452-28423-4', got '%s'", response.ISBN)
	}
}

func TestCreateBookMissingFields(t *testing.T) {
	// Test book creation with missing required fields
	bookData := map[string]interface{}{
		"title": "1984",
		// Missing author
		"year": 1948,
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestGetBooks(t *testing.T) {
	// Test getting all books
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	getBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response []Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Errorf("Error unmarshaling JSON: %v", err)
	}
}