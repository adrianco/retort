package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"
)

func TestBookAPI(t *testing.T) {
	// Create a temporary database for testing
	tmpDB := "test_books.db"
	store, err := NewBookStore(tmpDB)
	if err != nil {
		t.Fatal("Failed to create test database:", err)
	}
	defer store.Close()
	defer os.Remove(tmpDB)

	// Test health check
	t.Run("Health Check", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/health", nil)
		w := httptest.NewRecorder()
		store.handleHealthCheck(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
		}

		var response map[string]string
		json.Unmarshal(w.Body.Bytes(), &response)
		if response["status"] != "healthy" {
			t.Errorf("Expected status 'healthy', got '%s'", response["status"])
		}
	})

	// Test creating a book
	t.Run("Create Book", func(t *testing.T) {
		bookData := Book{
			Title:  "Test Book",
			Author: "Test Author",
			Year:   2023,
			ISBN:   "123-456-789",
		}

		jsonData, _ := json.Marshal(bookData)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
		}

		var response Book
		json.Unmarshal(w.Body.Bytes(), &response)
		if response.Title != bookData.Title {
			t.Errorf("Expected title '%s', got '%s'", bookData.Title, response.Title)
		}
		if response.Author != bookData.Author {
			t.Errorf("Expected author '%s', got '%s'", bookData.Author, response.Author)
		}
		if response.Year != bookData.Year {
			t.Errorf("Expected year %d, got %d", bookData.Year, response.Year)
		}
		if response.ISBN != bookData.ISBN {
			t.Errorf("Expected isbn '%s', got '%s'", bookData.ISBN, response.ISBN)
		}
	})

	// Test creating a book with missing required fields
	t.Run("Create Book Validation", func(t *testing.T) {
		// Test with missing title
		bookData := Book{
			Author: "Test Author",
			Year:   2023,
		}

		jsonData, _ := json.Marshal(bookData)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
		}
	})

	// Test getting all books
	t.Run("Get All Books", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books", nil)
		w := httptest.NewRecorder()
		store.handleGetBooks(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
		}

		var response []Book
		json.Unmarshal(w.Body.Bytes(), &response)
		if len(response) == 0 {
			t.Error("Expected at least one book")
		}
	})

	// Test getting books by author
	t.Run("Get Books by Author", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books?author=Test", nil)
		w := httptest.NewRecorder()
		store.handleGetBooks(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
		}

		var response []Book
		json.Unmarshal(w.Body.Bytes(), &response)
		// Should find books with "Test" in author name
	})

	// Test getting a specific book
	t.Run("Get Book by ID", func(t *testing.T) {
		// First create a book to get
		bookData := Book{
			Title:  "Another Test Book",
			Author: "Another Test Author",
			Year:   2022,
		}

		jsonData, _ := json.Marshal(bookData)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
		}

		var createdBook Book
		json.Unmarshal(w.Body.Bytes(), &createdBook)

		// Now test getting it
		req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		store.handleGetBook(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
		}

		var response Book
		json.Unmarshal(w.Body.Bytes(), &response)
		if response.ID != createdBook.ID {
			t.Errorf("Expected ID %d, got %d", createdBook.ID, response.ID)
		}
	})

	// Test updating a book
	t.Run("Update Book", func(t *testing.T) {
		// First create a book to update
		bookData := Book{
			Title:  "Original Title",
			Author: "Original Author",
			Year:   2020,
		}

		jsonData, _ := json.Marshal(bookData)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
		}

		var createdBook Book
		json.Unmarshal(w.Body.Bytes(), &createdBook)

		// Now update it
		updateData := Book{
			Title:  "Updated Title",
			Author: "Updated Author",
			Year:   2021,
			ISBN:   "updated-isbn",
		}

		jsonData, _ = json.Marshal(updateData)
		req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w = httptest.NewRecorder()
		store.handleUpdateBook(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
		}

		// Verify the update by fetching the book
		req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		store.handleGetBook(w, req)

		var response Book
		json.Unmarshal(w.Body.Bytes(), &response)
		if response.Title != updateData.Title {
			t.Errorf("Expected updated title '%s', got '%s'", updateData.Title, response.Title)
		}
		if response.Author != updateData.Author {
			t.Errorf("Expected updated author '%s', got '%s'", updateData.Author, response.Author)
		}
		if response.Year != updateData.Year {
			t.Errorf("Expected updated year %d, got %d", updateData.Year, response.Year)
		}
		if response.ISBN != updateData.ISBN {
			t.Errorf("Expected updated isbn '%s', got '%s'", updateData.ISBN, response.ISBN)
		}
	})

	// Test deleting a book
	t.Run("Delete Book", func(t *testing.T) {
		// First create a book to delete
		bookData := Book{
			Title:  "Book to Delete",
			Author: "Author of Deletion",
			Year:   2019,
		}

		jsonData, _ := json.Marshal(bookData)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
		}

		var createdBook Book
		json.Unmarshal(w.Body.Bytes(), &createdBook)

		// Now delete it
		req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		store.handleDeleteBook(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
		}

		// Verify it's deleted by trying to fetch it
		req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		store.handleGetBook(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
		}
	})
}