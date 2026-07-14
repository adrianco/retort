package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// Setup test database
func setupTestDB() *gorm.DB {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		panic("failed to connect to in-memory database")
	}
	db.AutoMigrate(&Book{})
	return db
}

// Helper to create a test handler
func createTestHandler(db *gorm.DB) *Handler {
	return NewHandler(db)
}

// Helper to create a book input as JSON
func createBookInput(title, author string, year int, isbn string) string {
	input := BookInput{
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}
	b, _ := json.Marshal(input)
	return string(b)
}

// Helper to make a request and return the response
func makeRequest(handler http.Handler, method, path string, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, nil)
	if body != "" {
		req.Body = io.NopCloser(bytes.NewBufferString(body))
		req.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	return w
}

// TestHealthCheck tests the /health endpoint
func TestHealthCheck(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", h.handleHealth)

	w := makeRequest(mux, "GET", "/health", "")

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "healthy", resp["status"])
}

// TestCreateBook tests creating a new book
func TestCreateBook(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/books", h.handleBooks)

	// Test valid book creation
	validBook := createBookInput("The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	w := makeRequest(mux, "POST", "/books", validBook)

	assert.Equal(t, http.StatusCreated, w.Code)
	var resp BookResponse
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "The Great Gatsby", resp.Title)
	assert.Equal(t, "F. Scott Fitzgerald", resp.Author)
	assert.Equal(t, 1925, resp.Year)
	assert.Equal(t, "978-0743273565", resp.ISBN)

	// Test validation - missing title
	emptyTitle := createBookInput("", "Author Name", 2020, "123-4567890123")
	w = makeRequest(mux, "POST", "/books", emptyTitle)
	assert.Equal(t, http.StatusBadRequest, w.Code)

	// Test validation - missing author
	emptyAuthor := createBookInput("Title", "", 2020, "123-4567890123")
	w = makeRequest(mux, "POST", "/books", emptyAuthor)
	assert.Equal(t, http.StatusBadRequest, w.Code)

	// Test validation - invalid year
	invalidYear := createBookInput("Title", "Author", 0, "123-4567890123")
	w = makeRequest(mux, "POST", "/books", invalidYear)
	assert.Equal(t, http.StatusBadRequest, w.Code)

	// Test validation - missing ISBN
	emptyISBN := createBookInput("Title", "Author", 2020, "")
	w = makeRequest(mux, "POST", "/books", emptyISBN)
	assert.Equal(t, http.StatusBadRequest, w.Code)

	// Test duplicate ISBN
	duplicateISBN := createBookInput("Another Book", "Another Author", 2021, "978-0743273565")
	w = makeRequest(mux, "POST", "/books", duplicateISBN)
	assert.Equal(t, http.StatusConflict, w.Code)
}

// TestGetBook tests getting a single book by ID
func TestGetBook(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/books", h.handleBooks)
	mux.HandleFunc("/books/{id}", h.handleBookByID)

	// Create a book first
	validBook := createBookInput("1984", "George Orwell", 1949, "978-0451524935")
	w := makeRequest(mux, "POST", "/books", validBook)
	assert.Equal(t, http.StatusCreated, w.Code)

	var created BookResponse
	json.Unmarshal(w.Body.Bytes(), &created)
	bookID := created.ID

	// Test getting the book
	w = makeRequest(mux, "GET", "/books/"+string(rune('0'+bookID)), "")
	assert.Equal(t, http.StatusOK, w.Code)
	json.Unmarshal(w.Body.Bytes(), &created)
	assert.Equal(t, "1984", created.Title)

	// Test getting non-existent book
	w = makeRequest(mux, "GET", "/books/9999", "")
	assert.Equal(t, http.StatusNotFound, w.Code)

	// Test invalid ID format
	w = makeRequest(mux, "GET", "/books/abc", "")
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

// TestUpdateBook tests updating a book
func TestUpdateBook(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/books", h.handleBooks)
	mux.HandleFunc("/books/{id}", h.handleBookByID)

	// Create a book first
	validBook := createBookInput("Pride and Prejudice", "Jane Austen", 1813, "978-0141439518")
	w := makeRequest(mux, "POST", "/books", validBook)
	assert.Equal(t, http.StatusCreated, w.Code)

	var created BookResponse
	json.Unmarshal(w.Body.Bytes(), &created)
	bookID := created.ID

	// Update the book
	updatedBook := createBookInput("Pride and Prejudice (Updated)", "Jane Austen", 1813, "978-0141439518")
	w = makeRequest(mux, "PUT", "/books/"+string(rune('0'+bookID)), updatedBook)
	assert.Equal(t, http.StatusOK, w.Code)

	var updated BookResponse
	json.Unmarshal(w.Body.Bytes(), &updated)
	assert.Equal(t, "Pride and Prejudice (Updated)", updated.Title)

	// Test updating non-existent book
	nonExistent := createBookInput("Non-existent", "Author", 2020, "123-456")
	w = makeRequest(mux, "PUT", "/books/9999", nonExistent)
	assert.Equal(t, http.StatusNotFound, w.Code)

	// Test validation on update - missing title
	emptyTitle := createBookInput("", "Author", 2020, "123-456")
	w = makeRequest(mux, "PUT", "/books/"+string(rune('0'+bookID)), emptyTitle)
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

// TestDeleteBook tests deleting a book
func TestDeleteBook(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/books", h.handleBooks)
	mux.HandleFunc("/books/{id}", h.handleBookByID)

	// Create a book first
	validBook := createBookInput("ToDelete", "Author Name", 2020, "123-4567890123")
	w := makeRequest(mux, "POST", "/books", validBook)
	assert.Equal(t, http.StatusCreated, w.Code)

	var created BookResponse
	json.Unmarshal(w.Body.Bytes(), &created)
	bookID := created.ID

	// Test deleting the book
	w = makeRequest(mux, "DELETE", "/books/"+string(rune('0'+bookID)), "")
	assert.Equal(t, http.StatusNoContent, w.Code)

	// Verify book is deleted
	w = makeRequest(mux, "GET", "/books/"+string(rune('0'+bookID)), "")
	assert.Equal(t, http.StatusNotFound, w.Code)

	// Test deleting non-existent book
	w = makeRequest(mux, "DELETE", "/books/9999", "")
	assert.Equal(t, http.StatusNotFound, w.Code)
}

// TestListBooks tests listing all books with optional author filter
func TestListBooks(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/books", h.handleBooks)

	// Create multiple books
	books := []struct {
		Title  string
		Author string
		Year   int
		ISBN   string
	}{
		{"Book 1", "Author A", 2020, "111-1111111111"},
		{"Book 2", "Author B", 2021, "222-2222222222"},
		{"Book 3", "Author A", 2022, "333-3333333333"},
	}

	for _, b := range books {
		validBook := createBookInput(b.Title, b.Author, b.Year, b.ISBN)
		w := makeRequest(mux, "POST", "/books", validBook)
		assert.Equal(t, http.StatusCreated, w.Code)
	}

	// Test listing all books
	w := makeRequest(mux, "GET", "/books", "")
	assert.Equal(t, http.StatusOK, w.Code)

	var resp BooksResponse
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, 3, resp.Total)
	assert.Len(t, resp.Books, 3)

	// Test filtering by author
	w = makeRequest(mux, "GET", "/books?author=Author+A", "")
	assert.Equal(t, http.StatusOK, w.Code)
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, 2, resp.Total)
	assert.Len(t, resp.Books, 2)
	for _, book := range resp.Books {
		assert.Equal(t, "Author A", book.Author)
	}
}

// TestBookModel tests the Book model
func TestBookModel(t *testing.T) {
	db := setupTestDB()

	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "978-1234567890",
	}

	// Create
	result := db.Create(&book)
	assert.Nil(t, result.Error)
	assert.Greater(t, book.ID, uint(0))

	// Read
	var found Book
	result = db.First(&found, book.ID)
	assert.Nil(t, result.Error)
	assert.Equal(t, "Test Book", found.Title)

	// Update
	found.Title = "Updated Title"
	result = db.Save(&found)
	assert.Nil(t, result.Error)

	var reRead Book
	result = db.First(&reRead, book.ID)
	assert.Nil(t, result.Error)
	assert.Equal(t, "Updated Title", reRead.Title)

	// Delete
	result = db.Delete(&found)
	assert.Nil(t, result.Error)

	// Verify deleted
	result = db.First(&found, book.ID)
	assert.Equal(t, gorm.ErrRecordNotFound, result.Error)
}

// TestInvalidJSON tests handling of invalid JSON
func TestInvalidJSON(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/books", h.handleBooks)

	// Test invalid JSON
	w := makeRequest(mux, "POST", "/books", "{invalid json}")
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

// TestMethodNotSupported tests handling of unsupported methods
func TestMethodNotSupported(t *testing.T) {
	db := setupTestDB()
	h := createTestHandler(db)

	mux := http.NewServeMux()
	mux.HandleFunc("/books", h.handleBooks)
	mux.HandleFunc("/books/{id}", h.handleBookByID)

	// Test DELETE on collection endpoint
	w := makeRequest(mux, "DELETE", "/books", "")
	assert.Equal(t, http.StatusMethodNotAllowed, w.Code)

	// Test POST on single book endpoint
	w = makeRequest(mux, "POST", "/books/1", "")
	assert.Equal(t, http.StatusMethodNotAllowed, w.Code)
}

// TestMain runs setup/teardown for all tests
func TestMain(m *testing.M) {
	// Set up
	code := m.Run()
	// Tear down
	os.Exit(code)
}
