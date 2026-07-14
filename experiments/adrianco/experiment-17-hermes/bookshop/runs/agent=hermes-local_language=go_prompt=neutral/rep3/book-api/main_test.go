package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHealthEndpoint(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", response["status"])
}

func TestBooksEndpoints(t *testing.T) {
	// First create a book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		Isbn:   "1234567890",
	}

	jsonBook, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", strings.NewReader(string(jsonBook)))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksPostHandler(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)

	// Parse the response to get the ID
	var createdBook Book
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)
	assert.NotEqual(t, 0, createdBook.ID)

	// Test getting all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	booksGetHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	// Test getting a single book by ID
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	bookGetHandler(w, req, createdBook.ID)

	assert.Equal(t, http.StatusOK, w.Code)

	// Test updating a book
	updatedBook := Book{
		Title:  "Updated Test Book",
		Author: "Updated Test Author",
		Year:   2024,
		Isbn:   "0987654321",
	}

	jsonUpdatedBook, _ := json.Marshal(updatedBook)
	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), strings.NewReader(string(jsonUpdatedBook)))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	bookPutHandler(w, req, createdBook.ID)

	assert.Equal(t, http.StatusOK, w.Code)

	// Test deleting a book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	bookDeleteHandler(w, req, createdBook.ID)

	assert.Equal(t, http.StatusNoContent, w.Code)
}

func TestBookValidation(t *testing.T) {
	// Test creating a book without title and author
	book := Book{
		Title:  "",
		Author: "",
		Year:   2023,
		Isbn:   "1234567890",
	}

	jsonBook, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", strings.NewReader(string(jsonBook)))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksPostHandler(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}
