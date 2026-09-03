package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	_ "github.com/mattn/go-sqlite3"
	"github.com/stretchr/testify/assert"
)

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", response["status"])
}

func TestCreateBook(t *testing.T) {
	// Initialize database for tests
	initDB()
	
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	
	// Verify the book was created by parsing the response
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)
	assert.NotEqual(t, 0, createdBook.ID)
	assert.Equal(t, "Test Book", createdBook.Title)
	assert.Equal(t, "Test Author", createdBook.Author)
}

func TestCreateBookMissingFields(t *testing.T) {
	// Initialize database for tests
	initDB()
	
	book := Book{
		Title:  "",
		Author: "",
		Year:   2023,
		ISBN:   "1234567890",
	}

	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestGetBookByID(t *testing.T) {
	// Initialize database for tests
	initDB()
	
	// Create a test book first
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	// Get the ID from the response
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)
	
	// Now test getting by ID
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	// Verify the book data
	var retrievedBook Book
	err = json.Unmarshal(w.Body.Bytes(), &retrievedBook)
	assert.NoError(t, err)
	assert.Equal(t, createdBook.ID, retrievedBook.ID)
	assert.Equal(t, "Test Book", retrievedBook.Title)
	assert.Equal(t, "Test Author", retrievedBook.Author)
}

func TestUpdateBook(t *testing.T) {
	// Initialize database for tests
	initDB()
	
	// Create a test book first
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	// Get the ID from the response
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)
	
	// Now update the book
	updatedBook := Book{
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2026,
		ISBN:   "3333333333",
	}
	
	jsonData, _ = json.Marshal(updatedBook)
	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	updateBookHandler(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	// Verify the update
	var updatedBookResp Book
	err = json.Unmarshal(w.Body.Bytes(), &updatedBookResp)
	assert.NoError(t, err)
	assert.Equal(t, createdBook.ID, updatedBookResp.ID)
	assert.Equal(t, "Updated Title", updatedBookResp.Title)
	assert.Equal(t, "Updated Author", updatedBookResp.Author)
	assert.Equal(t, 2026, updatedBookResp.Year)
	assert.Equal(t, "3333333333", updatedBookResp.ISBN)
}

func TestDeleteBook(t *testing.T) {
	// Initialize database for tests
	initDB()
	
	// Create a test book first
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	// Get the ID from the response
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)
	
	// Now delete the book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	deleteBookHandler(w, req)
	
	assert.Equal(t, http.StatusNoContent, w.Code)
}