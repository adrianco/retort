package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	healthHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	response := make(map[string]string)
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", response["status"])
}

func TestCreateBook(t *testing.T) {
	// Create a new book
	bookData := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	createBookHandler(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	response := Book{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Test Book", response.Title)
	assert.Equal(t, "Test Author", response.Author)
	assert.Equal(t, 2023, response.Year)
	assert.Equal(t, "1234567890", response.ISBN)
	assert.NotEqual(t, 0, response.ID)
}

func TestCreateBookMissingFields(t *testing.T) {
	// Try to create a book with missing required fields
	bookData := Book{
		Title:  "",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	createBookHandler(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestGetAllBooks(t *testing.T) {
	// Create a test book first
	bookData := Book{
		Title:  "Another Test Book",
		Author: "Another Test Author",
		Year:   2022,
		ISBN:   "0987654321",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	// Get all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	getBooksHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	books := []Book{}
	err := json.Unmarshal(w.Body.Bytes(), &books)
	assert.NoError(t, err)
	assert.NotEmpty(t, books)
}

func TestGetBookById(t *testing.T) {
	// Create a test book first
	bookData := Book{
		Title:  "Get Book Test",
		Author: "Get Book Author",
		Year:   2021,
		ISBN:   "1111111111",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	// Extract the created book ID from the response
	createdBook := Book{}
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)

	// Get the book by ID
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	response := Book{}
	err = json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Get Book Test", response.Title)
	assert.Equal(t, "Get Book Author", response.Author)
}

func TestUpdateBook(t *testing.T) {
	// Create a test book first
	bookData := Book{
		Title:  "Update Test Book",
		Author: "Update Test Author",
		Year:   2020,
		ISBN:   "2222222222",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	// Extract the created book ID from the response
	createdBook := Book{}
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)

	// Update the book
	updatedBookData := Book{
		Title:  "Updated Book Title",
		Author: "Updated Author",
		Year:   2024,
		ISBN:   "3333333333",
	}

	jsonData, _ = json.Marshal(updatedBookData)
	req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	updateBookHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	response := Book{}
	err = json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Updated Book Title", response.Title)
	assert.Equal(t, "Updated Author", response.Author)
	assert.Equal(t, 2024, response.Year)
	assert.Equal(t, "3333333333", response.ISBN)
	assert.Equal(t, createdBook.ID, response.ID)
}

func TestDeleteBook(t *testing.T) {
	// Create a test book first
	bookData := Book{
		Title:  "Delete Test Book",
		Author: "Delete Test Author",
		Year:   2019,
		ISBN:   "4444444444",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	// Extract the created book ID from the response
	createdBook := Book{}
	err := json.Unmarshal(w.Body.Bytes(), &createdBook)
	assert.NoError(t, err)

	// Delete the book
	req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	deleteBookHandler(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)

	// Verify the book is deleted by trying to fetch it
	req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestGetBookNotFound(t *testing.T) {
	req := httptest.NewRequest("GET", "/books/999999", nil)
	w := httptest.NewRecorder()
	getBookHandler(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestUpdateBookNotFound(t *testing.T) {
	updatedBookData := Book{
		Title:  "Updated Book Title",
		Author: "Updated Author",
		Year:   2024,
		ISBN:   "3333333333",
	}

	jsonData, _ := json.Marshal(updatedBookData)
	req := httptest.NewRequest("PUT", "/books/999999", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	updateBookHandler(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestDeleteBookNotFound(t *testing.T) {
	req := httptest.NewRequest("DELETE", "/books/999999", nil)
	w := httptest.NewRecorder()
	deleteBookHandler(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestFilterBooksByAuthor(t *testing.T) {
	// Create a few test books with different authors
	book1 := Book{
		Title:  "Book 1",
		Author: "Author A",
		Year:   2020,
		ISBN:   "1111111111",
	}

	book2 := Book{
		Title:  "Book 2",
		Author: "Author B",
		Year:   2021,
		ISBN:   "2222222222",
	}

	book3 := Book{
		Title:  "Book 3",
		Author: "Author A",
		Year:   2022,
		ISBN:   "3333333333",
	}

	// Create all books
	for _, book := range []Book{book1, book2, book3} {
		jsonData, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		createBookHandler(w, req)
	}

	// Filter books by author "Author A"
	req := httptest.NewRequest("GET", "/books?author=Author A", nil)
	w := httptest.NewRecorder()
	getBooksHandler(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	books := []Book{}
	err := json.Unmarshal(w.Body.Bytes(), &books)
	assert.NoError(t, err)
	assert.Len(t, books, 2) // Should return 2 books with author "Author A"

	// Verify that all returned books have the correct author
	for _, book := range books {
		assert.Contains(t, book.Author, "Author A")
	}
}
