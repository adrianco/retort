package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthEndpoint(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	handler := http.HandlerFunc(healthHandler)
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code 200, got %d", w.Code)
	}

	// Check response content
	var response HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Errorf("Error unmarshalling JSON: %v", err)
	}

	if response.Status != "OK" {
		t.Errorf("Expected status 'OK', got '%s'", response.Status)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	// Create a book
 jsonBody := `{
 "title": "Test Book",
 "author": "Test Author",
 "year": 2023,
 "isbn": "1234567890"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(jsonBody))
 req.Header.Set("Content-Type", "application/json")
 w := httptest.NewRecorder()

 createBookHandler(w, req)

 if w.Code != http.StatusCreated {
 t.Errorf("Expected status code 201, got %d", w.Code)
 }

 // Check response content
 var createdBook Book
 err := json.Unmarshal(w.Body.Bytes(), &createdBook)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if createdBook.Title != "Test Book" {
 t.Errorf("Expected title 'Test Book', got '%s'", createdBook.Title)
 }

 if createdBook.Author != "Test Author" {
 t.Errorf("Expected author 'Test Author', got '%s'", createdBook.Author)
 }

 if createdBook.Year != 2023 {
 t.Errorf("Expected year 2023, got %d", createdBook.Year)
 }

 if createdBook.ISBN != "1234567890" {
 t.Errorf("Expected ISBN '1234567890', got '%s'", createdBook.ISBN)
 }
}

func TestGetAllBooks(t *testing.T) {
	// Create a book first
 jsonBody := `{
 "title": "Another Book",
 "author": "Another Author",
 "year": 2020,
 "isbn": "0987654321"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(jsonBody))
 w := httptest.NewRecorder()

 createBookHandler(w, req)

 // Get all books
 req = httptest.NewRequest("GET", "/books", nil)
 w = httptest.NewRecorder()
 getBooksHandler(w, req)

 if w.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w.Code)
 }

 // Parse response
 var books []Book
 err := json.Unmarshal(w.Body.Bytes(), &books)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if len(books) != 1 {
 t.Errorf("Expected 1 book, got %d", len(books))
 }

 if books[0].Title != "Another Book" {
 t.Errorf("Expected title 'Another Book', got '%s'", books[0].Title)
 }
}

func TestGetBook(t *testing.T) {
	// Create a book first
 jsonBody := `{
 "title": "Test Book",
 "author": "Test Author",
 "year": 2023,
 "isbn": "1234567890"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(jsonBody))
 w := httptest.NewRecorder()

 createBookHandler(w, req)

 // Get the created book
 req = httptest.NewRequest("GET", "/books/1", nil)
 w = httptest.NewRecorder()
 getBookHandler(w, req)

 if w.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w.Code)
 }

 var book Book
 err := json.Unmarshal(w.Body.Bytes(), &book)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if book.Title != "Test Book" {
 t.Errorf("Expected title 'Test Book', got '%s'", book.Title)
 }

 if book.Author != "Test Author" {
 t.Errorf("Expected author 'Test Author', got '%s'", book.Author)
 }

 if book.Year != 2023 {
 t.Errorf("Expected year 2023, got %d", book.Year)
 }

 if book.ISBN != "1234567890" {
 t.Errorf("Expected ISBN '1234567890', got '%s'", book.ISBN)
 }
}