package main

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"testing"
)

func TestHealthEndpoint(t *testing.T) {
 req := httptest.NewRequest("GET", "/health", nil)
 w := httptest.NewResponseWriter()

 healthCheck(w, req)

 if w.Code != http.StatusOK {
  t.Errorf("Expected status code 200, got %d", w.Code)
 }

 var response map[string]string
 err := json.Unmarshal(w.Body().Bytes(), &response)
 if err != nil {
  t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if response["status"] != "healthy" {
  t.Errorf("Expected status to be healthy, got %s", response["status"])
 }
}

func TestCreateBook(t *testing.T) {
 book := Book{
  Title: "Test Book", 
  Author: "Test Author",
  Year: 2023,
  ISBN: "1234567890",
 }

 jsonBook, err := json.Marshal(book)
 if err != nil {
  t.Fatalf("Error marshalling book: %v", err)
 }

 req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBook))
 req.Header.Set("Content-Type", "application/json")
 w := httptest.NewResponseWriter()

 createBook(w, req)

 if w.Code != http.StatusCreated {
  t.Errorf("Expected status code 201, got %d", w.Code)
 }

 var createdBook Book
 err = json.Unmarshal(w.Body().Bytes(), &createdBook)
 if err != nil {
  t.Errorf("Error unmarshalling JSON: %v", err)
 }

 if createdBook.Title != "Test Book" {
  t.Errorf("Expected title 'Test Book', got '%s'", createdBook.Title)
 }

 if createdBook.Author != "Test Author" {
  t.Errorf("Expected author 'Test Author', got '%s'", createdBook.Author)
 }
}