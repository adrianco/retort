package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// setupTestRouter creates a test router with a fresh in-memory database.
func setupTestRouter(t *testing.T) (*gin.Engine, func()) {
	t.Helper()

	err := initDBWithPath(":memory:")
	if err != nil {
		t.Fatalf("Failed to setup test database: %v", err)
	}

	router := setupRouter()

	cleanup := func() {
		if db != nil {
			db.Close()
			db = nil
		}
	}

	return router, cleanup
}

func TestHealthCheck(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if resp["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	bookData := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}

	body, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if resp["title"] != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%v'", resp["title"])
	}

	if resp["id"] == nil {
		t.Error("Expected book ID to be set")
	}
}

func TestCreateBookValidation(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	// Test missing title
	bookData := map[string]interface{}{
		"author": "Test Author",
		"year":   2020,
		"isbn":   "123-456",
	}

	body, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing title, got %d", w.Code)
	}

	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["error"] != "Title is required" {
		t.Errorf("Expected error 'Title is required', got '%s'", resp["error"])
	}

	// Test missing author
	bookData = map[string]interface{}{
		"title": "Test Book",
		"year":  2020,
		"isbn":  "123-456",
	}

	body, _ = json.Marshal(bookData)
	req = httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing author, got %d", w.Code)
	}

	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["error"] != "Author is required" {
		t.Errorf("Expected error 'Author is required', got '%s'", resp["error"])
	}
}

func TestListBooks(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	// Create some test books
	books := []map[string]interface{}{
		{"title": "Book One", "author": "Author A", "year": 2020, "isbn": "isbn-1"},
		{"title": "Book Two", "author": "Author A", "year": 2021, "isbn": "isbn-2"},
		{"title": "Book Three", "author": "Author B", "year": 2022, "isbn": "isbn-3"},
	}

	for _, book := range books {
		body, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusCreated {
			t.Errorf("Failed to create test book: status %d", w.Code)
		}
	}

	// Test listing all books
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var bookList []map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &bookList); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if len(bookList) != 3 {
		t.Errorf("Expected 3 books, got %d", len(bookList))
	}

	// Test filtering by author
	req = httptest.NewRequest("GET", "/books?author=Author+A", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var filtered []map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if len(filtered) != 2 {
		t.Errorf("Expected 2 books for Author A, got %d", len(filtered))
	}
}

func TestGetBook(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	// Create a book first
	bookData := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "test-isbn-1",
	}

	body, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	var created map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &created)
	bookID := int(created["id"].(float64))

	// Get the book by ID
	req = httptest.NewRequest("GET", fmt.Sprintf("/books/%d", bookID), nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if resp["title"] != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%v'", resp["title"])
	}

	if resp["author"] != "Test Author" {
		t.Errorf("Expected author 'Test Author', got '%v'", resp["author"])
	}

	// Test getting non-existent book
	req = httptest.NewRequest("GET", "/books/9999", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 for non-existent book, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	// Create a book first
	bookData := map[string]interface{}{
		"title":  "Original Title",
		"author": "Original Author",
		"year":   2020,
		"isbn":   "update-isbn-1",
	}

	body, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	var created map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &created)
	bookID := int(created["id"].(float64))

	// Update the book
	updateData := map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
		"year":   2024,
		"isbn":   "updated-isbn-1",
	}

	body, _ = json.Marshal(updateData)
	req = httptest.NewRequest("PUT", fmt.Sprintf("/books/%d", bookID), bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	if resp["title"] != "Updated Title" {
		t.Errorf("Expected title 'Updated Title', got '%v'", resp["title"])
	}

	if resp["author"] != "Updated Author" {
		t.Errorf("Expected author 'Updated Author', got '%v'", resp["author"])
	}

	// JSON unmarshals numbers as float64 into interface{}
	if year, ok := resp["year"].(float64); !ok || int(year) != 2024 {
		t.Errorf("Expected year 2024, got '%v'", resp["year"])
	}

	// Test updating non-existent book
	req = httptest.NewRequest("PUT", "/books/9999", bytes.NewBuffer(body))
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 for non-existent book, got %d", w.Code)
	}

	// Test validation on update (missing title)
	badUpdate := map[string]interface{}{
		"author": "No Title Author",
		"year":   2024,
		"isbn":   "bad-isbn",
	}

	body, _ = json.Marshal(badUpdate)
	req = httptest.NewRequest("PUT", fmt.Sprintf("/books/%d", bookID), bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing title on update, got %d", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	// Create a book first
	bookData := map[string]interface{}{
		"title":  "Delete Me",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "delete-isbn-1",
	}

	body, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	var created map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &created)
	bookID := int(created["id"].(float64))

	// Delete the book
	req = httptest.NewRequest("DELETE", fmt.Sprintf("/books/%d", bookID), nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["message"] != "Book deleted successfully" {
		t.Errorf("Expected success message, got '%s'", resp["message"])
	}

	// Verify book is gone
	req = httptest.NewRequest("GET", fmt.Sprintf("/books/%d", bookID), nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 after deletion, got %d", w.Code)
	}

	// Test deleting non-existent book
	req = httptest.NewRequest("DELETE", "/books/9999", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 for non-existent book, got %d", w.Code)
	}
}

func TestListBooksEmpty(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var bookList []map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &bookList); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if len(bookList) != 0 {
		t.Errorf("Expected empty list, got %d books", len(bookList))
	}
}

func TestInvalidJSON(t *testing.T) {
	router, cleanup := setupTestRouter(t)
	defer cleanup()

	// Send invalid JSON
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer([]byte("{invalid json}")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for invalid JSON, got %d", w.Code)
	}
}

func init() {
	gin.SetMode(gin.TestMode)
}
