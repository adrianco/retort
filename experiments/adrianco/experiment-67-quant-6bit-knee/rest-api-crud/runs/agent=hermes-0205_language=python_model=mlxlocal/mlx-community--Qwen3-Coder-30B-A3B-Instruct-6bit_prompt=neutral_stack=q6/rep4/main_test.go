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

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthCheck(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
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

func TestCreateAndGetBook(t *testing.T) {
	// Clean up any existing database
	os.Remove("./books.db")

	// Reinitialize database
	initDB()
	defer db.Close()

	// Create a book
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "123-456-789",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books/", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBook(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status code %d, got %d", http.StatusCreated, w.Code)
	}

	// Parse response to get the created book ID
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Errorf("Error unmarshaling JSON: %v", err)
	}

	// Get the book by ID
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBook(w, req, strconv.Itoa(createdBook.ID))

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	// Verify the returned book matches what we created
	var returnedBook Book
	err = json.Unmarshal(w.Body.Bytes(), &returnedBook)
	if err != nil {
		t.Errorf("Error unmarshaling JSON: %v", err)
	}

	if returnedBook.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", returnedBook.Title)
	}

	if returnedBook.Author != "Test Author" {
		t.Errorf("Expected author 'Test Author', got '%s'", returnedBook.Author)
	}
}

func TestGetBooks(t *testing.T) {
	// Clean up any existing database
	os.Remove("./books.db")

	// Reinitialize database
	initDB()
	defer db.Close()

	// Create a book
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "123-456-789",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books/", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBook(w, req)

	// Get all books
	req = httptest.NewRequest("GET", "/books/", nil)
	w = httptest.NewRecorder()
	getBooks(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	// Verify we got at least one book
	var books []Book
	err := json.Unmarshal(w.Body.Bytes(), &books)
	if err != nil {
		t.Errorf("Error unmarshaling JSON: %v", err)
	}

	if len(books) == 0 {
		t.Errorf("Expected at least one book, got %d", len(books))
	}
}