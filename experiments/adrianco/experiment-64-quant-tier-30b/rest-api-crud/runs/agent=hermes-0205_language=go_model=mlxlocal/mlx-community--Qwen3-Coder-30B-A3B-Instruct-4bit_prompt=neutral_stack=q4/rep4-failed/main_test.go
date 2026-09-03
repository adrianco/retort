package main

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"testing"
)

func TestHealthEndpoint(t *testing.T) {
 req := httptest.NewRequest("GET", "/health", nil)
 w := httptest.NewRecorder()
 healthCheck(w, req)

 if w.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w.Code)
 }

 var response map[string]string
 err := json.Unmarshal(w.Body.Bytes(), &response)
 if err != nil {
 t.Errorf("Error unmarshaling response: %v", err)
 }

 if response["status"] != "healthy" {
 t.Errorf("Expected status healthy, got %s", response["status"])
 }
}

func TestCreateBook(t *testing.T) {
 book := Book{
 Title: "Test Book",
 Author: "Test Author",
 Year: 2023,
 ISBN: "1234567890",
 }

 jsonBody, err := json.Marshal(book)
 if err != nil {
 t.Fatalf("Error marshaling book: %v", err)
 }

 req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
 req.Header.Set("Content-Type", "application/json")
 w := httptest.NewRecorder()

 createBook(req, w)

 if w.Code != http.StatusCreated {
 t.Errorf("Expected status code 201, got %d", w.Code)
 }

 var createdBook Book
 err = json.Unmarshal(w.Body.Bytes(), &createdBook)
 if err != nil {
 t.Errorf("Error unmarshaling response: %v", err)
 }

 if createdBook.Title != book.Title {
 t.Errorf("Expected title %s, got %s", book.Title, createdBook.Title)
 }
}

func TestGetBook(t *testing.T) {
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(`{"title":"Test Book","author":"Test Author","year":2023,"isbn":"1234567890"}'))
 w := httptest.NewRecorder()
 createBook(req, w)

 var createdBook Book
 err := json.Unmarshal(w.Body.Bytes(), &createdBook)
 if err != nil {
 t.Errorf("Error unmarshaling response: %v", err)
 }

 req2 := httptest.NewRequest("GET", "/books/"+string(createdBook.ID), nil)
 w2 := httptest.NewRecorder()
 getBook(req2, w2)

 if w2.Code != http.StatusOK {
 t.Errorf("Expected status code 200, got %d", w2.Code)
 }
}

func TestListBooks(t *testing.T) {
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(`{"title":"Test Book","author":"Test Author","year":2023,"isbn":"1234567890"}'))
 w := httptest.NewRecorder()
 createBook(req, w)

 req2 := httptest.NewRequest("GET", "/books", nil)
 w2 := httptest.NewRecorder()
 listBooks(req2, w2)

 var books []Book
 err := json.Unmarshal(w2.Body.Bytes(), &books)
 if err != nil {
 t.Errorf("Error unmarshaling response: %v", err)
 }

 if len(books) == 0 {
 t.Error("Expected at least one book in the list")
 }
}

func TestDeleteBook(t *testing.T) {
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(`{"title":"Test Book","author":"Test Author","year":2023,"isbn":"1234567890"}"))
 w := httptest.NewRecorder()
 createBook(req, w)

 var createdBook Book
 err := json.Unmarshal(w.Body.Bytes(), &createdBook)
 if err != nil {
 t.Errorf("Error unmarshaling response: %v", err)
 }

 req2 := httptest.NewRequest("DELETE", "/books/"+string(createdBook.ID), nil)
 w2 := httptest.NewRecorder()
 deleteBook(req2, w2)

 if w2.Code != http.StatusNoContent {
 t.Errorf("Expected status code 204, got %d", w2.Code)
 }
}

func TestCreateBookWithoutRequiredFields(t *testing.T) {
 req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(`{"title":"","author":""}`))
 w := httptest.NewRecorder()
 createBook(req, w)

 if w.Code != http.StatusBadRequest {
 t.Errorf("Expected status code 400, got %d", w.Code)
 }
}