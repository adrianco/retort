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
	dbPath := "./test_books.db"
	store, err := NewBookStore(dbPath)
	if err != nil {
		t.Fatal("Failed to initialize test database:", err)
	}
	defer store.Close()
	defer os.Remove(dbPath)

	// Test health check
	t.Run("Health Check", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/health", nil)
		w := httptest.NewRecorder()
		store.handleHealth(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status 200, got %d", w.Code)
		}

		var response map[string]string
		err := json.Unmarshal(w.Body.Bytes(), &response)
		if err != nil {
			t.Fatal("Failed to unmarshal response:", err)
		}

		if response["status"] != "ok" {
			t.Errorf("Expected status 'ok', got '%s'", response["status"])
		}
	})

	// Test creating a book
	t.Run("Create Book", func(t *testing.T) {
		book := Book{
			Title:  "Test Book",
			Author: "Test Author",
			Year:   2023,
			ISBN:   "123-456-789",
		}

		body, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Errorf("Expected status 201, got %d", w.Code)
		}

		var createdBook Book
		err := json.Unmarshal(w.Body.Bytes(), &createdBook)
		if err != nil {
			t.Fatal("Failed to unmarshal created book:", err)
		}

		if createdBook.Title != book.Title {
			t.Errorf("Expected title '%s', got '%s'", book.Title, createdBook.Title)
		}

		if createdBook.Author != book.Author {
			t.Errorf("Expected author '%s', got '%s'", book.Author, createdBook.Author)
		}

		if createdBook.ID == 0 {
			t.Error("Expected book ID to be set")
		}
	})

	// Test creating a book without required fields
	t.Run("Create Book Missing Fields", func(t *testing.T) {
		book := Book{
			Title:  "",
			Author: "Test Author",
			Year:   2023,
		}

		body, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("Expected status 400 for missing title, got %d", w.Code)
		}
	})

	// Test getting all books
	t.Run("Get All Books", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books", nil)
		w := httptest.NewRecorder()
		store.handleGetBooks(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status 200, got %d", w.Code)
		}

		var books []Book
		err := json.Unmarshal(w.Body.Bytes(), &books)
		if err != nil {
			t.Fatal("Failed to unmarshal books:", err)
		}

		if len(books) == 0 {
			t.Error("Expected at least one book")
		}
	})

	// Test getting books by author
	t.Run("Get Books by Author", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books?author=Test", nil)
		w := httptest.NewRecorder()
		store.handleGetBooks(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status 200, got %d", w.Code)
		}

		var books []Book
		err := json.Unmarshal(w.Body.Bytes(), &books)
		if err != nil {
			t.Fatal("Failed to unmarshal books:", err)
		}

		// All books should have "Test" in their author name
		for _, book := range books {
			if !contains(book.Author, "Test") {
				t.Errorf("Book author '%s' does not contain 'Test'", book.Author)
			}
		}
	})

	// Test getting a specific book
	t.Run("Get Book by ID", func(t *testing.T) {
		// First create a book to get
		book := Book{
			Title:  "Specific Book",
			Author: "Specific Author",
			Year:   2023,
			ISBN:   "987-654-321",
		}

		body, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Fatalf("Failed to create test book: %d", w.Code)
		}

		var createdBook Book
		err := json.Unmarshal(w.Body.Bytes(), &createdBook)
		if err != nil {
			t.Fatal("Failed to unmarshal created book:", err)
		}

		// Now test getting it
		req = httptest.NewRequest("GET", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		store.handleGetBook(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status 200, got %d", w.Code)
		}

		var retrievedBook Book
		err = json.Unmarshal(w.Body.Bytes(), &retrievedBook)
		if err != nil {
			t.Fatal("Failed to unmarshal retrieved book:", err)
		}

		if retrievedBook.ID != createdBook.ID {
			t.Errorf("Expected ID %d, got %d", createdBook.ID, retrievedBook.ID)
		}
	})

	// Test updating a book
	t.Run("Update Book", func(t *testing.T) {
		// First create a book to update
		book := Book{
			Title:  "Original Title",
			Author: "Original Author",
			Year:   2023,
			ISBN:   "original-isbn",
		}

		body, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Fatalf("Failed to create test book for update: %d", w.Code)
		}

		var createdBook Book
		err := json.Unmarshal(w.Body.Bytes(), &createdBook)
		if err != nil {
			t.Fatal("Failed to unmarshal created book:", err)
		}

		// Now update it
		updatedBook := Book{
			Title:  "Updated Title",
			Author: "Updated Author",
			Year:   2024,
			ISBN:   "updated-isbn",
		}

		body, _ = json.Marshal(updatedBook)
		req = httptest.NewRequest("PUT", "/books/"+strconv.Itoa(createdBook.ID), bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w = httptest.NewRecorder()
		store.handleUpdateBook(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status 200, got %d", w.Code)
		}

		var returnedBook Book
		err = json.Unmarshal(w.Body.Bytes(), &returnedBook)
		if err != nil {
			t.Fatal("Failed to unmarshal updated book:", err)
		}

		if returnedBook.Title != updatedBook.Title {
			t.Errorf("Expected title '%s', got '%s'", updatedBook.Title, returnedBook.Title)
		}

		if returnedBook.Author != updatedBook.Author {
			t.Errorf("Expected author '%s', got '%s'", updatedBook.Author, returnedBook.Author)
		}
	})

	// Test deleting a book
	t.Run("Delete Book", func(t *testing.T) {
		// First create a book to delete
		book := Book{
			Title:  "Book to Delete",
			Author: "Author of Deletion",
			Year:   2023,
			ISBN:   "delete-isbn",
		}

		body, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		store.handleCreateBook(w, req)

		if w.Code != http.StatusCreated {
			t.Fatalf("Failed to create test book for deletion: %d", w.Code)
		}

		var createdBook Book
		err := json.Unmarshal(w.Body.Bytes(), &createdBook)
		if err != nil {
			t.Fatal("Failed to unmarshal created book:", err)
		}

		// Now delete it
		req = httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(createdBook.ID), nil)
		w = httptest.NewRecorder()
		store.handleDeleteBook(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status 200, got %d", w.Code)
		}
	})
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(substr) == 0 ||
		(len(s) > len(substr) && (s[:len(substr)] == substr || s[len(s)-len(substr):] == substr ||
			contains(s[1:], substr))))
}