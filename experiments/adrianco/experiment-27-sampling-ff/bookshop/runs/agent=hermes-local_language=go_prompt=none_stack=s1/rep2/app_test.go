package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// setupTest creates a test database and Gin router
func setupTest(t *testing.T) (*sql.DB, *gin.Engine) {
	t.Helper()

	gin.SetMode(gin.TestMode)

	d, err := openDB()
	if err != nil {
		t.Fatalf("Failed to open test database: %v", err)
	}

	// Save the test db so handlers can use it
	db = d

	r := gin.Default()
	r.GET("/health", healthHandler)
	r.POST("/books", createBookHandler)
	r.GET("/books", listBooksHandler)
	r.GET("/books/:id", getBookHandler)
	r.PUT("/books/:id", updateBookHandler)
	r.DELETE("/books/:id", deleteBookHandler)

	return d, r
}

// teardownTest closes the test database
func teardownTest(t *testing.T, d *sql.DB) {
	t.Helper()
	if d != nil {
		d.Close()
	}
}

// insertBook inserts a book into the test database and returns its ID
func insertBook(t *testing.T, d *sql.DB, title, author string, year int, isbn string) int {
	t.Helper()
	result, err := d.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", title, author, year, isbn)
	if err != nil {
		t.Fatalf("Failed to insert book: %v", err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		t.Fatalf("Failed to get last insert ID: %v", err)
	}
	return int(id)
}

// TestHealthCheck tests the health check endpoint
func TestHealthCheck(t *testing.T) {
	_, r := setupTest(t)
	defer teardownTest(t, db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Errorf("Expected status 'ok', got %v", resp["status"])
	}
}

// TestCreateBook tests creating a new book
func TestCreateBook(t *testing.T) {
	_, r := setupTest(t)
	defer teardownTest(t, db)

	payload := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0743273565",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var resp Book
	json.Unmarshal(w.Body.Bytes(), &resp)

	if resp.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got '%s'", resp.Title)
	}
	if resp.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got '%s'", resp.Author)
	}
	if resp.Year != 1925 {
		t.Errorf("Expected year 1925, got %d", resp.Year)
	}
	if resp.ISBN != "978-0743273565" {
		t.Errorf("Expected isbn '978-0743273565', got '%s'", resp.ISBN)
	}
	if resp.ID == 0 {
		t.Error("Expected non-zero ID")
	}
}

// TestCreateBookValidation tests input validation for creating a book
func TestCreateBookValidation(t *testing.T) {
	_, r := setupTest(t)
	defer teardownTest(t, db)

	tests := []struct {
		name       string
		payload    map[string]interface{}
		wantStatus int
	}{
		{
			name: "missing title",
			payload: map[string]interface{}{
				"author": "Test Author",
				"year":   2020,
				"isbn":   "123",
			},
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "missing author",
			payload: map[string]interface{}{
				"title": "Test Book",
				"year":  2020,
				"isbn":  "123",
			},
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "empty title",
			payload: map[string]interface{}{
				"title":  "",
				"author": "Test Author",
				"year":   2020,
				"isbn":   "123",
			},
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "empty author",
			payload: map[string]interface{}{
				"title":  "Test Book",
				"author": "",
				"year":   2020,
				"isbn":   "123",
			},
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body, _ := json.Marshal(tt.payload)
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")
			r.ServeHTTP(w, req)

			if w.Code != tt.wantStatus {
				t.Errorf("Expected status %d, got %d. Body: %s", tt.wantStatus, w.Code, w.Body.String())
			}
		})
	}
}

// TestListBooks tests listing all books
func TestListBooks(t *testing.T) {
	d, r := setupTest(t)
	defer teardownTest(t, db)

	// Insert test data
	id1 := insertBook(t, d, "Book One", "Author A", 2020, "isbn-1")
	_ = insertBook(t, d, "Book Two", "Author B", 2021, "isbn-2")
	_ = insertBook(t, d, "Book Three", "Author A", 2022, "isbn-3")

	// List all books
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}

	// Verify the first book has the correct ID
	if books[0].ID != id1 {
		t.Errorf("Expected first book ID %d, got %d", id1, books[0].ID)
	}
}

// TestListBooksByAuthor tests filtering books by author
func TestListBooksByAuthor(t *testing.T) {
	d, r := setupTest(t)
	defer teardownTest(t, db)

	_ = insertBook(t, d, "Book One", "Author A", 2020, "isbn-1")
	_ = insertBook(t, d, "Book Two", "Author B", 2021, "isbn-2")
	_ = insertBook(t, d, "Book Three", "Author A", 2022, "isbn-3")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books?author=Author+A", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 2 {
		t.Errorf("Expected 2 books for Author A, got %d", len(books))
	}
}

// TestGetBook tests getting a single book by ID
func TestGetBook(t *testing.T) {
	d, r := setupTest(t)
	defer teardownTest(t, db)

	id := insertBook(t, d, "Test Book", "Test Author", 2023, "isbn-test")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", fmt.Sprintf("/books/%d", id), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", book.Title)
	}
	if book.Author != "Test Author" {
		t.Errorf("Expected author 'Test Author', got '%s'", book.Author)
	}
}

// TestGetBookNotFound tests getting a non-existent book
func TestGetBookNotFound(t *testing.T) {
	_, r := setupTest(t)
	defer teardownTest(t, db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/9999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

// TestUpdateBook tests updating a book
func TestUpdateBook(t *testing.T) {
	d, r := setupTest(t)
	defer teardownTest(t, db)

	id := insertBook(t, d, "Old Title", "Old Author", 2020, "old-isbn")

	payload := map[string]interface{}{
		"title":  "New Title",
		"author": "New Author",
		"year":   2024,
		"isbn":   "new-isbn",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", fmt.Sprintf("/books/%d", id), bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp Book
	json.Unmarshal(w.Body.Bytes(), &resp)

	if resp.Title != "New Title" {
		t.Errorf("Expected title 'New Title', got '%s'", resp.Title)
	}
	if resp.Author != "New Author" {
		t.Errorf("Expected author 'New Author', got '%s'", resp.Author)
	}
	if resp.Year != 2024 {
		t.Errorf("Expected year 2024, got %d", resp.Year)
	}
}

// TestDeleteBook tests deleting a book
func TestDeleteBook(t *testing.T) {
	d, r := setupTest(t)
	defer teardownTest(t, db)

	id := insertBook(t, d, "To Delete", "Author", 2023, "isbn-del")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("/books/%d", id), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	// Verify the book is deleted
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", fmt.Sprintf("/books/%d", id), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 after deletion, got %d", w.Code)
	}
}

// TestDeleteBookNotFound tests deleting a non-existent book
func TestDeleteBookNotFound(t *testing.T) {
	_, r := setupTest(t)
	defer teardownTest(t, db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/9999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

// TestUpdateBookNotFound tests updating a non-existent book
func TestUpdateBookNotFound(t *testing.T) {
	_, r := setupTest(t)
	defer teardownTest(t, db)

	payload := map[string]interface{}{
		"title":  "New Title",
		"author": "New Author",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/9999", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

// TestEmptyListBooks tests listing books when the database is empty
func TestEmptyListBooks(t *testing.T) {
	_, r := setupTest(t)
	defer teardownTest(t, db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("Expected 0 books, got %d", len(books))
	}
}
