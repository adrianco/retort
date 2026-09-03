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
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBook(w, req)
	
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status code %d, got %d", http.StatusCreated, w.Code)
	}
	
	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
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
		t.Errorf("Expected ISBN '%s', got '%s'", book.ISBN, response.ISBN)
	}
}

func TestCreateBookMissingFields(t *testing.T) {
	book := Book{
		Title:  "",
		Author: "",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBook(w, req)
	
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestGetBooks(t *testing.T) {
	// First create a test book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBook(w, req)
	
	// Now test getting all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	getBooks(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}
	
	var response []Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if len(response) == 0 {
		t.Error("Expected at least one book in the response")
	}
}

func TestGetBook(t *testing.T) {
	// First create a test book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBook(w, req)
	
	// Get the ID of the created book
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	// Test getting the specific book
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBook(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
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
	// First create a test book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBook(w, req)
	
	// Get the ID of the created book
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	// Update the book
	updatedBook := Book{
		Title:  "Updated Test Book",
		Author: "Updated Test Author",
		Year:   2024,
		ISBN:   "0987654321",
	}
	
	jsonData, _ = json.Marshal(updatedBook)
	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w = httptest.NewRecorder()
	updateBook(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}
	
	var response Book
	err = json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
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

func TestDeleteBook(t *testing.T) {
	// First create a test book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBook(w, req)
	
	// Get the ID of the created book
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	// Delete the book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	deleteBook(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}
	
	var response map[string]string
	err = json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}
	
	if response["message"] != "Book deleted successfully" {
		t.Errorf("Expected success message, got '%s'", response["message"])
	}
}

func TestGetNonExistentBook(t *testing.T) {
	req := httptest.NewRequest("GET", "/books/999", nil)
	w := httptest.NewRecorder()
	getBook(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status code %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestDeleteNonExistentBook(t *testing.T) {
	req := httptest.NewRequest("DELETE", "/books/999", nil)
	w := httptest.NewRecorder()
	deleteBook(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status code %d, got %d", http.StatusNotFound, w.Code)
	}
}