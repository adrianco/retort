package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"

	"github.com/stretchr/testify/assert"
)

// Setup a fresh database for testing
func setupTestDB() {
	// Remove any existing database file
	os.Remove("./books.db")
	
	// Initialize the database
	initDB()
}

func TestHealthEndpoint(t *testing.T) {
	setupTestDB()
	
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
	setupTestDB()
	
	// Create a book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonBook, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBook))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Test Book", response.Title)
	assert.Equal(t, "Test Author", response.Author)
	assert.Equal(t, 2023, response.Year)
	assert.Equal(t, "1234567890", response.ISBN)
}

func TestGetBook(t *testing.T) {
	setupTestDB()
	
	// First create a book to get
	book := Book{
		Title:  "Get Test Book",
		Author: "Get Test Author",
		Year:   2022,
		ISBN:   "0987654321",
	}
	
	jsonBook, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBook))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	var createdBook Book
	json.Unmarshal(w.Body.Bytes(), &createdBook)
	
	// Now test getting the book by ID
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Get Test Book", response.Title)
	assert.Equal(t, "Get Test Author", response.Author)
}

func TestGetBooks(t *testing.T) {
	setupTestDB()
	
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	
	getBooksHandler(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response []Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.GreaterOrEqual(t, len(response), 0)
}

func TestUpdateBook(t *testing.T) {
	setupTestDB()
	
	// First create a book to update
	book := Book{
		Title:  "Update Test Book",
		Author: "Update Test Author",
		Year:   2021,
		ISBN:   "1111111111",
	}
	
	jsonBook, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBook))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	var createdBook Book
	json.Unmarshal(w.Body.Bytes(), &createdBook)
	
	// Now update the book
	updatedBook := Book{
		Title:  "Updated Test Book",
		Author: "Updated Test Author",
		Year:   2024,
		ISBN:   "2222222222",
	}
	
	jsonUpdatedBook, _ := json.Marshal(updatedBook)
	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonUpdatedBook))
	req.Header.Set("Content-Type", "application/json")
	
	w = httptest.NewRecorder()
	updateBookHandler(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Updated Test Book", response.Title)
	assert.Equal(t, "Updated Test Author", response.Author)
	assert.Equal(t, 2024, response.Year)
	assert.Equal(t, "2222222222", response.ISBN)
}

func TestDeleteBook(t *testing.T) {
	setupTestDB()
	
	// First create a book to delete
	book := Book{
		Title:  "Delete Test Book",
		Author: "Delete Test Author",
		Year:   2020,
		ISBN:   "3333333333",
	}
	
	jsonBook, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBook))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	var createdBook Book
	json.Unmarshal(w.Body.Bytes(), &createdBook)
	
	// Now delete the book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	deleteBookHandler(w, req)
	
	assert.Equal(t, http.StatusNoContent, w.Code)
}

func TestCreateBookWithMissingRequiredFields(t *testing.T) {
	setupTestDB()
	
	// Create a book without required fields
	book := Book{
		Title: "",
		Author: "",
		Year:   2023,
		ISBN:   "1234567890",
	}
	
	jsonBook, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonBook))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	createBookHandler(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
}