package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

// setupTestDB creates a temporary in-memory database for testing
func setupTestDB() error {
	var err error
	db, err = sql.Open("sqlite3", ":memory:")
	if err != nil {
		return err
	}
	createTable()
	return nil
}

// setupRouter creates a test router
func setupRouter() *gin.Engine {
	r := gin.Default()
	r.GET("/health", healthCheck)
	books := r.Group("/books")
	{
		books.GET("", listBooks)
		books.POST("", createBook)
		books.GET("/:id", getBook)
		books.PUT("/:id", updateBook)
		books.DELETE("/:id", deleteBook)
	}
	return r
}

// TestHealthCheck tests the health check endpoint
func TestHealthCheck(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r := setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response HealthResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "ok", response.Status)
}

// TestCreateBook tests creating a new book
func TestCreateBook(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	w := httptest.NewRecorder()
	
	// Test with valid data
	validBook := BookInput{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}
	jsonData, _ := json.Marshal(validBook)
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r := setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "The Great Gatsby", response["title"])
	assert.Equal(t, "F. Scott Fitzgerald", response["author"])

	// Test with missing title
	w = httptest.NewRecorder()
	invalidBook := BookInput{
		Title:  "",
		Author: "Some Author",
		Year:   2020,
	}
	jsonData, _ = json.Marshal(invalidBook)
	req, _ = http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w = httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)

	// Test with missing author
	w = httptest.NewRecorder()
	invalidBook2 := BookInput{
		Title: "Some Book",
		Author: "",
		Year:  2020,
	}
	jsonData, _ = json.Marshal(invalidBook2)
	req, _ = http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	w = httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

// TestListBooks tests listing all books
func TestListBooks(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	// Create some test books
	books := []BookInput{
		{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "111"},
		{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "222"},
		{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "333"},
	}

	for _, book := range books {
		w := httptest.NewRecorder()
		jsonData, _ := json.Marshal(book)
		req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		
		r := setupRouter()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusCreated, w.Code)
	}

	// Test listing all books
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r := setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response []Book
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, 3, len(response))

	// Test filtering by author
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books?author=Author+A", nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, 2, len(response))
	for _, book := range response {
		assert.Equal(t, "Author A", book.Author)
	}
}

// TestGetBook tests getting a single book by ID
func TestGetBook(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	// Create a book first
	w := httptest.NewRecorder()
	book := BookInput{Title: "Test Book", Author: "Test Author", Year: 2023, ISBN: "123"}
	jsonData, _ := json.Marshal(book)
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r := setupRouter()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)

	// Get the created book's ID from response
	var createResponse map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &createResponse)
	bookID := int(createResponse["id"].(float64))

	// Test getting the book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/"+string(rune('0'+bookID)), nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "Test Book", response.Title)

	// Test getting a non-existent book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/9999", nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

// TestUpdateBook tests updating a book
func TestUpdateBook(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	// Create a book
	w := httptest.NewRecorder()
	book := BookInput{Title: "Original Title", Author: "Original Author", Year: 2020, ISBN: "111"}
	jsonData, _ := json.Marshal(book)
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r := setupRouter()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)

	// Get the created book's ID
	var createResponse map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &createResponse)
	bookID := int(createResponse["id"].(float64))

	// Update the book
	w = httptest.NewRecorder()
	updatedBook := BookInput{Title: "Updated Title", Author: "Updated Author", Year: 2021, ISBN: "222"}
	jsonData, _ = json.Marshal(updatedBook)
	req, _ = http.NewRequest("PUT", "/books/"+string(rune('0'+bookID)), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "Updated Title", response["title"])
	assert.Equal(t, 2021, int(response["year"].(float64)))

	// Test updating non-existent book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("PUT", "/books/9999", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

// TestDeleteBook tests deleting a book
func TestDeleteBook(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	// Create a book
	w := httptest.NewRecorder()
	book := BookInput{Title: "To Delete", Author: "Author", Year: 2020, ISBN: "111"}
	jsonData, _ := json.Marshal(book)
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r := setupRouter()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)

	// Get the created book's ID
	var createResponse map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &createResponse)
	bookID := int(createResponse["id"].(float64))

	// Delete the book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/"+string(rune('0'+bookID)), nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)

	// Verify the book is deleted
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/"+string(rune('0'+bookID)), nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)

	// Test deleting non-existent book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/9999", nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

// TestInvalidBookID tests handling of invalid book IDs
func TestInvalidBookID(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	// Test with invalid ID for GET
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/abc", nil)
	r := setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)

	// Test with invalid ID for PUT
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("PUT", "/books/abc", nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)

	// Test with invalid ID for DELETE
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/abc", nil)
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

// TestEmptyDatabase tests listing books when database is empty
func TestEmptyDatabase(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r := setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response []Book
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, 0, len(response))
}

// TestTitleValidation tests that title validation works for updates
func TestTitleValidationOnUpdate(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_ = setupTestDB()

	// Create a book
	w := httptest.NewRecorder()
	book := BookInput{Title: "Original", Author: "Author", Year: 2020, ISBN: "111"}
	jsonData, _ := json.Marshal(book)
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r := setupRouter()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)

	// Get the created book's ID
	var createResponse map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &createResponse)
	bookID := int(createResponse["id"].(float64))

	// Try to update with empty title
	w = httptest.NewRecorder()
	updatedBook := BookInput{Title: "", Author: "New Author", Year: 2021, ISBN: "222"}
	jsonData, _ = json.Marshal(updatedBook)
	req, _ = http.NewRequest("PUT", "/books/"+string(rune('0'+bookID)), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	r = setupRouter()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

// Cleanup database file after tests
func TestMain(m *testing.M) {
	// Run tests
	code := m.Run()
	
	// Cleanup
	os.Remove("books.db")
	
	os.Exit(code)
}
