package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCreateBook(t *testing.T) {
	// Create a handler with a shared database connection for testing
	db, err := initDB()
	assert.NoError(t, err)
	
	// Create a handler
	handler := &Handler{db: NewSQLiteStore(db)}

	// Create a test book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	// Convert to JSON
	jsonData, _ := json.Marshal(book)

	// Create request
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	// Create response recorder
	rr := httptest.NewRecorder()

	// Call handler
	handler.createBook(rr, req)

	// Check status code
	assert.Equal(t, http.StatusCreated, rr.Code)

	// Check response body
	var responseBook Book
	err = json.Unmarshal(rr.Body.Bytes(), &responseBook)
	assert.NoError(t, err)
	assert.Equal(t, book.Title, responseBook.Title)
	assert.Equal(t, book.Author, responseBook.Author)
	assert.Equal(t, book.Year, responseBook.Year)
	assert.Equal(t, book.ISBN, responseBook.ISBN)
	assert.NotEqual(t, 0, responseBook.ID)
}

func TestGetBook(t *testing.T) {
	// Create a handler with a shared database connection for testing
	db, err := initDB()
	assert.NoError(t, err)

	// Create a handler
	handler := &Handler{db: NewSQLiteStore(db)}

	// First create a book to get
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	// Save the book
	err = handler.db.CreateBook(&book)
	assert.NoError(t, err)

	// Create request
	req := httptest.NewRequest("GET", "/books/1", nil)

	// Create response recorder
	rr := httptest.NewRecorder()

	// Call handler
	handler.getBook(rr, req)

	// Check status code
	assert.Equal(t, http.StatusOK, rr.Code)

	// Check response body
	var responseBook Book
	err = json.Unmarshal(rr.Body.Bytes(), &responseBook)
	assert.NoError(t, err)
	assert.Equal(t, book.Title, responseBook.Title)
	assert.Equal(t, book.Author, responseBook.Author)
	assert.Equal(t, book.Year, responseBook.Year)
	assert.Equal(t, book.ISBN, responseBook.ISBN)
	assert.Equal(t, 1, responseBook.ID)
}

func TestHealthCheck(t *testing.T) {
	// Create a handler with a shared database connection for testing
	db, err := initDB()
	assert.NoError(t, err)

	// Create a handler
	handler := &Handler{db: NewSQLiteStore(db)}

	// Create request
	req := httptest.NewRequest("GET", "/health", nil)

	// Create response recorder
	rr := httptest.NewRecorder()

	// Call handler
	handler.healthCheck(rr, req)

	// Check status code
	assert.Equal(t, http.StatusOK, rr.Code)

	// Check response body
	var response map[string]string
	err = json.Unmarshal(rr.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", response["status"])
}