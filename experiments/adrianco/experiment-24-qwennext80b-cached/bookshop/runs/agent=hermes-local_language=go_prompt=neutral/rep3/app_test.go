package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

// Setup test environment
func setupTestDB() error {
	// Use a test database file
	testDB, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		return err
	}
	db = testDB

	// Create table for testing
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`

	_, err = db.Exec(createTableSQL)
	return err
}

// Helper to create a test router
func createTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	
	// Books endpoints
	r.GET("/books", GetBooks)
	r.POST("/books", CreateBook)
	r.GET("/books/:id", GetBook)
	r.PUT("/books/:id", UpdateBook)
	r.DELETE("/books/:id", DeleteBook)
	r.GET("/health", HealthCheck)
	
	return r
}

// Helper to marshal a request body
func marshalRequest(body interface{}) (*bytes.Buffer, error) {
	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}
	return bytes.NewBuffer(jsonBody), nil
}

// Test Health Check endpoint
func TestHealthCheck(t *testing.T) {
	gin.SetMode(gin.TestMode)
	
	r := gin.Default()
	r.GET("/health", HealthCheck)

	req, _ := http.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	
	var response HealthCheckResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.Equal(t, "healthy", response.Status)
	assert.Equal(t, "connected", response.Database)
	assert.NotEmpty(t, response.Timestamp)
}

// Test Create Book endpoint
func TestCreateBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}

	r := createTestRouter()

	// Test valid book creation
	validBook := BookInput{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}

	body, err := marshalRequest(validBook)
	if err != nil {
		t.Fatalf("Failed to marshal request body: %v", err)
	}

	req, _ := http.NewRequest("POST", "/books", body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.Equal(t, validBook.Title, response["title"])
	assert.Equal(t, validBook.Author, response["author"])
	assert.Equal(t, int64(validBook.Year), int64(response["year"].(float64)))
	assert.Equal(t, validBook.ISBN, response["isbn"])
	assert.NotEmpty(t, response["id"])
}

// Test Create Book with validation errors - check for required fields
func TestCreateBookValidationError(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	r.POST("/books", CreateBook)

	// Test missing title - use a request that will fail binding
	validBook := BookInput{
		Author: "Some Author",
		Year:   2024,
		ISBN:   "1234567890",
	}

	body, _ := marshalRequest(validBook)
	req, _ := http.NewRequest("POST", "/books", body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	// The binding error will contain error details
	assert.Contains(t, response["error"], "Title")

	// Test missing author
	bookWithoutAuthor := BookInput{
		Title: "Some Book",
		Year:  2024,
		ISBN:  "1234567890",
	}

	body, _ = marshalRequest(bookWithoutAuthor)
	req, _ = http.NewRequest("POST", "/books", body)
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var response2 map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response2)
	assert.Contains(t, response2["error"], "Author")
}

// Test Get Books (all)
func TestGetBooks(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}

	r := createTestRouter()

	// Insert test data
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Book 1", "Author A", 2020, "111-1111111111")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Book 2", "Author B", 2021, "222-2222222222")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Book 3", "Author A", 2022, "333-3333333333")

	req, _ := http.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response []Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.Len(t, response, 3)
}

// Test Get Books with author filter
func TestGetBooksByAuthor(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}

	r := createTestRouter()

	// Insert test data
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Book 1", "Author A", 2020, "111-1111111111")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Book 2", "Author B", 2021, "222-2222222222")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Book 3", "Author A", 2022, "333-3333333333")

	// Filter by Author A
	req, _ := http.NewRequest("GET", "/books?author=Author+A", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response []Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.Len(t, response, 2)
	for _, book := range response {
		assert.Equal(t, "Author A", book.Author)
	}
}

// Test Get Book by ID
func TestGetBookByID(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}

	r := createTestRouter()

	// Insert test data
	result, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Test Book", "Test Author", 2023, "444-4444444444")
	id, _ := result.LastInsertId()

	req, _ := http.NewRequest("GET", "/books/"+string(rune(id+'0')), nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.Equal(t, id, response.ID)
	assert.Equal(t, "Test Book", response.Title)
	assert.Equal(t, "Test Author", response.Author)
}

// Test Get Book by non-existent ID
func TestGetBookNotFound(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	r.GET("/books/:id", GetBook)

	req, _ := http.NewRequest("GET", "/books/999999", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

// Test Update Book
func TestUpdateBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}

	r := createTestRouter()

	// Insert test data
	result, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Original Title", "Original Author", 2020, "555-5555555555")
	id, _ := result.LastInsertId()

	// Update the book
	updateBook := BookInput{
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2024,
		ISBN:   "666-6666666666",
	}

	body, _ := marshalRequest(updateBook)
	req, _ := http.NewRequest("PUT", "/books/"+string(rune(id+'0')), body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.Equal(t, id, response.ID)
	assert.Equal(t, "Updated Title", response.Title)
	assert.Equal(t, "Updated Author", response.Author)
}

// Test Update non-existent book
func TestUpdateBookNotFound(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	r.PUT("/books/:id", UpdateBook)

	updateBook := BookInput{
		Title:  "New Title",
		Author: "New Author",
		Year:   2024,
		ISBN:   "777-7777777777",
	}

	body, _ := marshalRequest(updateBook)
	req, _ := http.NewRequest("PUT", "/books/999999", body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

// Test Delete Book
func TestDeleteBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}

	r := createTestRouter()

	// Insert test data
	result, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
		"Book to Delete", "Delete Author", 2020, "888-8888888888")
	id, _ := result.LastInsertId()

	req, _ := http.NewRequest("DELETE", "/books/"+string(rune(id+'0')), nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "Book deleted successfully", response["message"])

	// Verify the book was deleted
	var count int
	db.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&count)
	assert.Equal(t, 0, count)
}

// Test Delete non-existent book
func TestDeleteBookNotFound(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	r.DELETE("/books/:id", DeleteBook)

	req, _ := http.NewRequest("DELETE", "/books/999999", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}
