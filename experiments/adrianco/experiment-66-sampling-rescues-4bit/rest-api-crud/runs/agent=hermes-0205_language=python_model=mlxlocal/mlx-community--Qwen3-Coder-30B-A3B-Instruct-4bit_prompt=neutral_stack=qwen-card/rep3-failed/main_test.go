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
 healthHandler(w, req)

 if w.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w.Code)
 }

 var response HealthResponse
 if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
 t.Errorf("Failed to unmarshal response: %v", err)
 }

 if response.Status != "OK" {
 t.Errorf("Expected status 'OK', got '%s'", response.Status)
 }
}

func TestCreateAndGetBook(t *testing.T) {
	// Create a new book
 bookData := BookRequest{
 Title: "Test Book",
 Author: "Test Author",
 Year: 2023,
 ISBN: "1234567890",
 }
 
 jsonBody, err := json.Marshal(bookData)
 if err != nil {
 t.Fatalf("Failed to marshal book data: %v", err)
 }

 req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
 req.Header.Set("Content-Type", "application/json")
 w := httptest.NewRecorder()

 postBook(w, req)

 if w.Code != http.StatusCreated {
 t.Errorf("Expected status code 201, got %d", w.Code)
 }

 var createdBook Book
 if err := json.Unmarshal(w.Body.Bytes(), &createdBook); err != nil {
 t.Fatalf("Failed to unmarshal response: %v", err)
 }

 // Test get by ID
 w2 := httptest.NewRecorder()
 req2 := httptest.NewRequest("GET", "/books/"+string(createdBook.ID), nil)
 getBook(w2, req2, createdBook.ID)

 if w2.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w2.Code)
 }

 var retrievedBook Book
 if err := json.Unmarshal(w.Body.Bytes(), &retrievedBook); err != nil {
 t.Fatalf("Failed to unmarshal response: %v", err)
 }

 if retrievedBook.Title != createdBook.Title {
 t.Errorf("Expected title '%s', got '%s'", createdBook.Title, retrievedBook.Title)
 }

 if retrievedBook.Author != createdBook.Author {
 t.Errorf("Expected author '%s', got '%s'", createdBook.Author, retrievedBook.Author)
 }
}

func TestGetAllBooks(t *testing.T) {
 req := httptest.NewRequest("GET", "/books", nil)
 w := httptest.NewRecorder()
 getBooks(w, req)

 if w.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w.Code)
 }

 var books []Book
 if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
 t.Fatalf("Failed to unmarshal response: %v", err)
 }

 // Check that we have at least one book (the one created in previous test)
 if len(books) == 0 {
 t.Error("Expected at least one book in the database")
 }
}

func TestUpdateBook(t *testing.T) {
	// First create a book to update
 bookData := BookRequest{
 Title: "Original Title",
 Author: "Original Author",
 Year: 2023,
 ISBN: "1234567890",
 }
 
 jsonBody, err := json.Marshal(bookData)
 if err != nil {
 t.Fatalf("Failed to marshal book data: %v", err)
 }

 req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
 w := httptest.NewRecorder()

 postBook(w, req)

 var createdBook Book
 if err := json.Unmarshal(w.Body.Bytes(), &createdBook); err != nil {
 t.Fatalf("Failed to unmarshal response: %v", err)
 }

 // Update the book
 updatedBookData := BookRequest{
 Title: "Updated Title",
 Author: "Updated Author",
 Year: 2024,
 ISBN: "1234567890",
 }

 jsonBody2, err := json.Marshal(updatedBookData)
 if err != nil {
 t.Fatalf("Failed to marshal updated book data: %v", err)
 }

 w2 := httptest.NewRecorder()
 req2 := httptest.NewRequest("PUT", "/books/"+string(createdBook.ID), bytes.NewBuffer(jsonBody2))
 req2.Header.Set("Content-Type", "application/json")
 putBook(w2, req2, createdBook.ID)

 if w2.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w2.Code)
 }

 var updatedBook Book
 if err := json.Unmarshal(w.Body.Bytes(), &updatedBook); err != nil {
 t.Fatalf("Failed to unmarshal response: %v", err)
 }

 if updatedBook.Title != "Updated Title" {
 t.Errorf("Expected title 'Updated Title', got '%s'", updatedBook.Title)
 }

 if updatedBook.Author != "Updated Author" {
 t.Errorf("Expected author 'Updated Author', got '%s'", updatedBook.Author)
 }
}

func TestDeleteBook(t *testing.T) {
	// First create a book to delete
 bookData := BookRequest{
 Title: "Book to Delete",
 Author: "Delete Author",
 Year: 2023,
 ISBN: "1234567890",
 }

 jsonBody, err := json.Marshal(bookData)
 if err != nil {
 t.Fatalf("Failed to marshal book data: %v", err)
 }

 req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
 w := httptest.NewRecorder()

 postBook(w, req)

 var createdBook Book
 if err := json.Unmarshal(w.Body.Bytes(), &createdBook); err != nil {
 t.Fatalf("Failed to unmarshal response: %v", err)
 }

 w2 := httptest.NewRecorder()
 req2 := httptest.NewRequest("DELETE", "/books/"+string(createdBook.ID), nil)
 deleteBook(w2, createdBook.ID)

 if w2.Code != http.StatusNoContent {
 t.Errorf("Expected status code 204, got %d", w2.Code)
 }
}