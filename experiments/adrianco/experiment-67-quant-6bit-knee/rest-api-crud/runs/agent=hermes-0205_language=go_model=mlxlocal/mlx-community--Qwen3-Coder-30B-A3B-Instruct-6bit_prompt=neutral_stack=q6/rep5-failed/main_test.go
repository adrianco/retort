package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHealthCheck(t *testing.T) {
	bookStore, err := NewBookStore()
	assert.NoError(t, err)
	defer bookStore.Close()

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	bookStore.HealthHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response map[string]string
	err = json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", response["status"])
}

func TestCreateBook(t *testing.T) {
	bookStore, err := NewBookStore()
	assert.NoError(t, err)
	defer bookStore.Close()

	// Test valid book creation
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	bookStore.CreateBookHandler(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	var response Book
	err = json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, book.Title, response.Title)
	assert.Equal(t, book.Author, response.Author)
	assert.Equal(t, book.Year, response.Year)
	assert.Equal(t, book.ISBN, response.ISBN)
	assert.NotEqual(t, 0, response.ID)
}

func TestCreateBookMissingRequiredFields(t *testing.T) {
	bookStore, err := NewBookStore()
	assert.NoError(t, err)
	defer bookStore.Close()

	// Test missing title
	book := Book{
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	bookStore.CreateBookHandler(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var response map[string]string
	err = json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Contains(t, response["error"], "Title is required")
}