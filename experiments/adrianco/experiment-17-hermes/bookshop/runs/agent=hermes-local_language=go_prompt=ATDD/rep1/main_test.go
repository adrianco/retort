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

func TestBookAPI(t *testing.T) {
	// Initialize database
	db, err := initDB()
	assert.NoError(t, err)
	defer db.Close()

	// Initialize router
	r := initRouter(db)

	// Test health endpoint
	t.Run("Health Check", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/health", nil)
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		var response map[string]string
		err := json.Unmarshal(w.Body.Bytes(), &response)
		assert.NoError(t, err)
		assert.Equal(t, "healthy", response["status"])
	})

	// Test creating a book
	t.Run("Create Book", func(t *testing.T) {
		bookData := `{"title": "Test Book", "author": "Test Author", "year": 2023, "isbn": "1234567890"}`
		req := httptest.NewRequest("POST", "/books", strings.NewReader(bookData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusCreated, w.Code)
		var response Book
		err := json.Unmarshal(w.Body.Bytes(), &response)
		assert.NoError(t, err)
		assert.Equal(t, "Test Book", response.Title)
		assert.Equal(t, "Test Author", response.Author)
	})

	// Test listing books
	t.Run("List Books", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books", nil)
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		var response []Book
		err := json.Unmarshal(w.Body.Bytes(), &response)
		assert.NoError(t, err)
		assert.NotEmpty(t, response)
	})

	// Test getting a single book
	t.Run("Get Book", func(t *testing.T) {
		// First create a book to get
		bookData := `{"title": "Another Test Book", "author": "Another Test Author", "year": 2024, "isbn": "0987654321"}`
		req := httptest.NewRequest("POST", "/books", strings.NewReader(bookData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusCreated, w.Code)

		var createdBook Book
		err := json.Unmarshal(w.Body.Bytes(), &createdBook)
		assert.NoError(t, err)

		// Now get that book using the proper ID format
		req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		var response Book
		err = json.Unmarshal(w.Body.Bytes(), &response)
		assert.NoError(t, err)
		assert.Equal(t, createdBook.ID, response.ID)
	})
}
