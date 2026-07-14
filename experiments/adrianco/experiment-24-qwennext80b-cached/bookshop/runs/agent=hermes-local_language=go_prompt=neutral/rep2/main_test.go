package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Setup test database
func setupTestDB() error {
	// Use in-memory database for testing
	if db != nil {
		db.Close()
	}
	var err error
	db, err = sql.Open("sqlite3", ":memory:")
	if err != nil {
		return err
	}
	return createTable()
}

func TestHealthHandler(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	healthHandler(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)
	var response HealthResponse
	err := json.Unmarshal(rec.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.Equal(t, "ok", response.Status)
}

func TestCreateBook(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	book := Book{Title: "Test Book", Author: "Test Author", Year: 2024, ISBN: "123-456"}
	body, _ := json.Marshal(book)

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	assert.Equal(t, http.StatusCreated, rec.Code)
	var response Book
	err = json.Unmarshal(rec.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.Equal(t, "Test Book", response.Title)
	assert.Equal(t, "Test Author", response.Author)
	assert.Equal(t, 2024, response.Year)
	assert.Equal(t, "123-456", response.ISBN)
	assert.Greater(t, response.ID, 0)
}

func TestCreateBookMissingTitle(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	book := Book{Title: "", Author: "Test Author"}
	body, _ := json.Marshal(book)

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	assert.Equal(t, http.StatusBadRequest, rec.Code)
	// Check that response body contains the error message
	responseBody := rec.Body.String()
	assert.Contains(t, responseBody, "Title is required")
}

func TestCreateBookMissingAuthor(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	book := Book{Title: "Test Book", Author: ""}
	body, _ := json.Marshal(book)

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	assert.Equal(t, http.StatusBadRequest, rec.Code)
	// Check that response body contains the error message
	responseBody := rec.Body.String()
	assert.Contains(t, responseBody, "Author is required")
}

func TestGetBook(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	// Create a book first
	book := Book{Title: "Get Test Book", Author: "Get Test Author"}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	// Get the created book
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rec = httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)
	var response Book
	err = json.Unmarshal(rec.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.Equal(t, "Get Test Book", response.Title)
}

func TestGetBookNotFound(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	rec := httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusNotFound, rec.Code)
}

func TestUpdateBook(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	// Create a book
	book := Book{Title: "Original Title", Author: "Original Author"}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	// Update the book
	updatedBook := Book{ID: 1, Title: "Updated Title", Author: "Updated Author", Year: 2025, ISBN: "999-888"}
	body, _ = json.Marshal(updatedBook)
	req = httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewBuffer(body))
	rec = httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)
	var response Book
	err = json.Unmarshal(rec.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.Equal(t, "Updated Title", response.Title)
	assert.Equal(t, "Updated Author", response.Author)
	assert.Equal(t, 2025, response.Year)
}

func TestUpdateBookNotFound(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	book := Book{ID: 999, Title: "Nonexistent", Author: "Nobody"}
	body, _ := json.Marshal(book)

	req := httptest.NewRequest(http.MethodPut, "/books/999", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusNotFound, rec.Code)
}

func TestDeleteBook(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	// Create a book
	book := Book{Title: "Delete Me", Author: "Delete Author"}
	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	// Delete the book
	req = httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	rec = httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusNoContent, rec.Code)

	// Verify it's deleted
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rec = httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusNotFound, rec.Code)
}

func TestDeleteBookNotFound(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
	rec := httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusNotFound, rec.Code)
}

func TestListBooks(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	// Create multiple books
	books := []Book{
		{Title: "Book 1", Author: "Author A"},
		{Title: "Book 2", Author: "Author B"},
		{Title: "Book 3", Author: "Author A"},
	}

	for _, b := range books {
		body, _ := json.Marshal(b)
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
		rec := httptest.NewRecorder()
		booksHandler(rec, req)
	}

	// List all books
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)
	var response []Book
	err = json.Unmarshal(rec.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.Len(t, response, 3)
}

func TestListBooksByAuthor(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	// Create books with different authors
	books := []Book{
		{Title: "Book 1", Author: "Author A"},
		{Title: "Book 2", Author: "Author B"},
		{Title: "Book 3", Author: "Author A"},
	}

	for _, b := range books {
		body, _ := json.Marshal(b)
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
		rec := httptest.NewRecorder()
		booksHandler(rec, req)
	}

	// Filter by author
	req := httptest.NewRequest(http.MethodGet, "/books?author=Author+A", nil)
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)
	var response []Book
	err = json.Unmarshal(rec.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.Len(t, response, 2)
	for _, book := range response {
		assert.Equal(t, "Author A", book.Author)
	}
}

func TestInvalidJSON(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader("invalid json"))
	rec := httptest.NewRecorder()
	booksHandler(rec, req)

	assert.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestInvalidBookID(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodGet, "/books/abc", nil)
	rec := httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestMethodNotAllowed(t *testing.T) {
	err := setupTestDB()
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodPatch, "/books/1", nil)
	rec := httptest.NewRecorder()
	bookHandler(rec, req)

	assert.Equal(t, http.StatusMethodNotAllowed, rec.Code)

	req = httptest.NewRequest(http.MethodPatch, "/books", nil)
	rec = httptest.NewRecorder()
	booksHandler(rec, req)

	assert.Equal(t, http.StatusMethodNotAllowed, rec.Code)
}

func TestMain(m *testing.M) {
	// Clean up database after tests
	code := m.Run()
	if db != nil {
		db.Close()
	}
	// Remove test database file if it exists
	os.Remove("books.db")
	os.Exit(code)
}
