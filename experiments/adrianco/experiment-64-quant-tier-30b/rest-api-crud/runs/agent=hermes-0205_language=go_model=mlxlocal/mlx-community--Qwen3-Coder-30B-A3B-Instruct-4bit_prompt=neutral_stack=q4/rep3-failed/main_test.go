package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestHealthEndpoint(t *testing.T) {
	// Setup test server
 api, err := NewBookAPI("test.db")
 if err != nil {
 t.Fatalf("Failed to create book API: %v", err)
 }

 defer api.db.Close()
 defer os.Remove("test.db")

 req := httptest.NewRequest("GET", "/health", nil)
 w := httptest.NewRecorder()

 api.HealthHandler(w, req)

 if w.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w.Code)
 }

 var response map[string]string
 err = json.Unmarshal(w.Body.Bytes(), &response)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if response["status"] != "healthy" {
 t.Errorf("Expected status 'healthy', got '%s'", response["status"])
 }
}

func TestCreateBook(t *testing.T) {
 api, err := NewBookAPI("test.db")
 if err != nil {
 t.Fatalf("Failed to create book API: %v", err)
 }
 defer api.db.Close()
 defer os.Remove("test.db")

 // Create a book
 bookJSON := `{
 "title": "Test Book",
 "author": "Test Author",
 "year": 2024,
 "isbn": "1234567890"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(bookJSON))
 req.Header.Set("Content-Type", "application/json")

 w := httptest.NewRecorder()
 api.CreateBook(w, req)

 if w.Code != http.StatusCreated {
 t.Errorf("Expected status code 201, got %d", w.Code)
 }

 var response Book
 err = json.Unmarshal(w.Body.Bytes(), &response)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if response.Title != "Test Book" {
 t.Errorf("Expected title 'Test Book', got '%s'", response.Title)
 }
 if response.Author != "Test Author" {
 t.Errorf("Expected author 'Test Author', got '%s'", response.Author)
 }
 if response.Year != 2024 {
 t.Errorf("Expected year 2024, got %d", response.Year)
 }
 if response.ISBN != "1234567890" {
 t.Errorf("Expected ISBN '1234567890', got '%s'", response.ISBN)
 }
}

func TestGetBook(t *testing.T) {
 api, err := NewBookAPI("test.db")
 if err != nil {
 t.Fatalf("Failed to create book API: %v", err)
 }
 defer api.db.Close()
 defer os.Remove("test.db")

 // Create a book first
 bookJSON := `{
 "title": "Test Book",
 "author": "Test Author",
 "year": 2024,
 "isbn": "1234567890"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(bookJSON))
 w := httptest.NewRecorder()
 api.CreateBook(w, req)

 // Get the book by ID
 req2 := httptest.NewRequest("GET", "/books/1", nil)
 w2 := httptest.NewRecorder()
 api.GetBook(w2, req2)

 if w2.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w2.Code)
 }

 var response Book
 err = json.Unmarshal(w2.Body.Bytes(), &response)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if response.Title != "Test Book" {
 t.Errorf("Expected title 'Test Book', got '%s'", response.Title)
 }
 if response.Author != "Test Author" {
 t.Errorf("Expected author 'Test Author', got '%s'", response.Author)
 }
 if response.Year != 2024 {
 t.Errorf("Expected year 2024, got %d", response.Year)
 }
 if response.ISBN != "1234567890" {
 t.Errorf("Expected ISBN '1234567890', got '%s'", response.ISBN)
 }
}

func TestUpdateBook(t *testing.T) {
 api, err := NewBookAPI("test.db")
 if err != nil {
 t.Fatalf("Failed to create book API: %v", err)
 }
 defer api.db.Close()
 defer os.Remove("test.db")

 // Create a book first
 bookJSON := `{
 "title": "Test Book",
 "author": "Test Author",
 "year": 2024,
 "isbn": "1234567890"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(bookJSON))
 w := httptest.NewRecorder()
 api.CreateBook(w, req)

 // Update the book
 updateJSON := `{
 "title": "Updated Book",
 "author": "Updated Author",
 "year": 2025,
 "isbn": "0987654321"
}`
 req2 := httptest.NewRequest("PUT", "/books/1", bytes.NewBufferString(updateJSON))
 req2.Header.Set("Content-Type", "application/json")
 w2 := httptest.NewRecorder()
 api.UpdateBook(w2, req2)

 if w2.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w2.Code)
 }

 var response Book
 err = json.Unmarshal(w2.Body.Bytes(), &response)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if response.Title != "Updated Book" {
 t.Errorf("Expected title 'Updated Book', got '%s'", response.Title)
 }
 if response.Author != "Updated Author" {
 t.Errorf("Expected author 'Updated Author', got '%s'", response.Author)
 }
 if response.Year != 2025 {
 t.Errorf("Expected year 2025, got %d", response.Year)
 }
 if response.ISBN != "0987654321" {
 t.Errorf("Expected ISBN '0987654321', got '%s'", response.ISBN)
 }
}

func TestDeleteBook(t *testing.T) {
 api, err := NewBookAPI("test.db")
 if err != nil {
 t.Fatalf("Failed to create book API: %v", err)
 }
 defer api.db.Close()
 defer os.Remove("test.db")

 // Create a book first
 bookJSON := `{
 "title": "Test Book",
 "author": "Test Author",
 "year": 2024,
 "isbn": "1234567890"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(bookJSON))
 w := httptest.NewRecorder()
 api.CreateBook(w, req)

 // Delete the book
 req2 := httptest.NewRequest("DELETE", "/books/1", nil)
 w2 := httptest.NewRecorder()
 api.DeleteBook(w2, req2)

 if w2.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w2.Code)
 }

 var response map[string]string
 err = json.Unmarshal(w2.Body.Bytes(), &response)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if response["message"] != "Book deleted successfully" {
 t.Errorf("Expected message 'Book deleted successfully', got '%s'", response["message"])
 }
}

func TestGetAllBooks(t *testing.T) {
 api, err := NewBookAPI("test.db")
 if err != nil {
 t.Fatalf("Failed to create book API: %v", err)
 }
 defer api.db.Close()
 defer os.Remove("test.db")

 // Create a book first
 bookJSON := `{
 "title": "Test Book",
 "author": "Test Author",
 "year": 2024,
 "isbn": "1234567890"
}`
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(bookJSON))
 w := httptest.NewRecorder()
 api.CreateBook(w, req)

 // Get all books
 req2 := httptest.NewRequest("GET", "/books", nil)
 w2 := httptest.NewRecorder()
 api.GetAllBooks(w2, req2)

 if w2.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w2.Code)
 }

 var response []Book
 err = json.Unmarshal(w2.Body.Bytes(), &response)
 if err != nil {
 t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if len(response) != 1 {
 t.Errorf("Expected 1 book, got %d", len(response))
 }

 if response[0].Title != "Test Book" {
 t.Errorf("Expected title 'Test Book', got '%s'", response[0].Title)
 }
}

func TestGetBookNotFound(t *testing.T) {
 api, err := NewBookAPI("test.db")
 if err != nil {
 t.Fatalf("Failed to create book API: %v", err)
 }
 defer api.db.Close()
 defer os.Remove("test.db")

 // Try to get a non-existent book
 req := httptest.NewRequest("GET", "/books/999", nil)
 w := httptest.NewRecorder()
 api.GetBook(w, req)

 if w.Code != http.StatusNotFound {
 t.Errorf("Expected status code 404, got %d", w.Code)
 }
}