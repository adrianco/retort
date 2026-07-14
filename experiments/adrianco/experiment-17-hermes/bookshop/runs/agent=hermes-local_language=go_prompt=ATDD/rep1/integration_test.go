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

func TestBookAPIIntegration(t *testing.T) {
	// Initialize database
	db, err := initDB()
	assert.NoError(t, err)
	defer db.Close()

	// Initialize router
	r := initRouter(db)

	// Test all CRUD operations
	t.Run("Complete CRUD Flow", func(t *testing.T) {
		// 1. Create a book
		bookData := `{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "9780451524935"}`
		req := httptest.NewRequest("POST", "/books", strings.NewReader(bookData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusCreated, w.Code)
		var createdBook Book
		err := json.Unmarshal(w.Body.Bytes(), &createdBook)
		assert.NoError(t, err)
		assert.Equal(t, "1984", createdBook.Title)
		assert.Equal(t, "George Orwell", createdBook.Author)
		assert.Equal(t, 1948, createdBook.Year)
		assert.Equal(t, "9780451524935", createdBook.ISBN)

		// 2. List all books and verify it contains our book
		req = httptest.NewRequest("GET", "/books", nil)
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		var books []Book
		err = json.Unmarshal(w.Body.Bytes(), &books)
		assert.NoError(t, err)
		assert.NotEmpty(t, books)

		// 3. Get the book by ID
		req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		var retrievedBook Book
		err = json.Unmarshal(w.Body.Bytes(), &retrievedBook)
		assert.NoError(t, err)
		assert.Equal(t, createdBook.ID, retrievedBook.ID)
		assert.Equal(t, createdBook.Title, retrievedBook.Title)

		// 4. Update the book
		updateData := `{"title": "1984 - Updated Edition", "author": "George Orwell", "year": 1948, "isbn": "9780451524935"}`
		req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), strings.NewReader(updateData))
		req.Header.Set("Content-Type", "application/json")
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		var updatedBook Book
		err = json.Unmarshal(w.Body.Bytes(), &updatedBook)
		assert.NoError(t, err)
		assert.Equal(t, "1984 - Updated Edition", updatedBook.Title)

		// 5. Delete the book
		req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusNoContent, w.Code)

		// 6. Verify the book is deleted
		req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusNotFound, w.Code)
	})

	// Test filtering by author
	t.Run("Filter Books by Author", func(t *testing.T) {
		// Create two books with same author
		book1 := `{"title": "Book 1", "author": "Author A", "year": 2020, "isbn": "123"}`
		book2 := `{"title": "Book 2", "author": "Author B", "year": 2021, "isbn": "456"}`
		
		req := httptest.NewRequest("POST", "/books", strings.NewReader(book1))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusCreated, w.Code)

		req = httptest.NewRequest("POST", "/books", strings.NewReader(book2))
		req.Header.Set("Content-Type", "application/json")
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusCreated, w.Code)

		// Filter by author A
		req = httptest.NewRequest("GET", "/books?author=Author+A", nil)
		w = httptest.NewRecorder()
		r.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		var books []Book
		err = json.Unmarshal(w.Body.Bytes(), &books)
		assert.NoError(t, err)
		assert.Len(t, books, 1)
		assert.Equal(t, "Author A", books[0].Author)
	})
}
