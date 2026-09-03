package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCreateBook(t *testing.T) {
	// Create a test book
	book := Book{
 Title: "Test Book",
 Author: "Test Author",
 Year: 2023,
 ISBN: "1234567890",
}

	// Create request
	requestBody, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(requestBody))
	req.Header.Set("Content-Type", "application/json")

	// Create response recorder
 rr := httptest.NewRecorder()

 // Call the handler
 handler := http.HandlerFunc(createBook)
 handler.ServeHTTP(rr, req)

 // Check the status code
 if status := rr.Code; status != http.StatusCreated {
 t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusCreated)
 }

 // Check the response body
 expected := `{"id":1,"title":"Test Book","author":"Test Author","year":2023,"isbn":"1234567890"}`
 if rr.Body.String() != expected {
 t.Errorf("handler returned unexpected body: got %v want %v", rr.Body.String(), expected)
 }
}

func TestGetBook(t *testing.T) {
	// First create a book
	book := Book{
 Title: "Test Book",
 Author: "Test Author",
 Year: 2023,
 ISBN: "1234567890",
}

 // Create request
 req := httptest.NewRequest("POST", "/books", nil) // We'll just test the GET part
 rr := httptest.NewRecorder()

 // Call the handler
 handler := http.HandlerFunc(createBook)
 handler.ServeHTTP(rr, req)

 // Now test GET
 req = httptest.NewRequest("GET", "/books/1", nil)
 handler = http.HandlerFunc(getBook)
 handler.ServeHTTP(rr, req)

 // Check the status code
 if status := rr.Code; status != http.StatusOK {
 t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
 }
}

func TestUpdateBook(t *testing.T) {
	// First create a book
	book := Book{
 Title: "Test Book",
 Author: "Test Author",
 Year: 2023,
 ISBN: "1234567890",
}

 // Create request
 req := httptest.NewRequest("POST", "/books", nil) // We'll just test the GET part
 rr := httptest.NewRecorder()

 // Call the handler
 handler := http.HandlerFunc(createBook)
 handler.ServeHTTP(rr, req)

 // Now test update
 updateBook := Book{
 ID: 1,
 Title: "Updated Book",
 Author: "Updated Author",
 Year: 2024,
 ISBN: "9876543210",
}

 requestBody, _ := json.Marshal(updateBook)
 req = httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(requestBody))
 req.Header.Set("Content-Type", "application/json")

 rr = httptest.NewRecorder()
 handler = http.HandlerFunc(updateBook)
 handler.ServeHTTP(rr, req)

 // Check the status code
 if status := rr.Code; status != http.StatusOK {
 t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
 }
}

func TestDeleteBook(t *testing.T) {
	// First create a book
	book := Book{
 Title: "Test Book",
 Author: "Test Author",
 Year: 2023,
 ISBN: "1234567890",
}

 // Create request
 req := httptest.NewRequest("POST", "/books", nil) // We'll just test the GET part
 rr := httptest.NewRecorder()

 // Call the handler
 handler := http.HandlerFunc(createBook)
 handler.ServeHTTP(rr, req)

 // Now delete it
 req = httptest.NewRequest("DELETE", "/books/1", nil)
 rr = httptest.NewRecorder()
 handler = http.HandlerFunc(deleteBook)
 handler.ServeHTTP(rr, req)

 // Check the status code
 if status := rr.Code; status != http.StatusNoContent {
 t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusNoContent)
 }
}