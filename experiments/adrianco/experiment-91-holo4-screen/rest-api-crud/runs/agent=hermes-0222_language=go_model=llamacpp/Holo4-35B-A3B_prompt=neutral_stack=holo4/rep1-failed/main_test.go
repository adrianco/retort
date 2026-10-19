package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func setupTestDB(t *testing.T) {
	// Use a test database file
	os.Remove("./test_books.db")
	dbFile = "./test_books.db"
	if err := initDB(); err != nil {
		t.Fatalf("Failed to initialize test database: %v", err)
	}
}

func TestHealthCheck(t *testing.T) {
	setupTestDB(t)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("Expected status 'ok', got %s", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	setupTestDB(t)
	body, _ := json.Marshal(CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	w := httptest.NewRecorder()
	createBook(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if book.Title != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got %s", book.Title)
	}
	if book.ID != 1 {
		t.Errorf("Expected ID 1, got %d", book.ID)
	}
}

func TestCreateBookValidation(t *testing.T) {
	setupTestDB(t)

	// Test missing title
	body, _ := json.Marshal(CreateBookRequest{
		Author: "Test Author",
	})
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	w := httptest.NewRecorder()
	createBook(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing title, got %d", w.Code)
	}

	// Test missing author
	body, _ = json.Marshal(CreateBookRequest{
		Title: "Test Book",
	})
	req = httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	w = httptest.NewRecorder()
	createBook(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing author, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	setupTestDB(t)

	// Create a couple of books
	createBook(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/books",
		bytes.NewReader(func() []byte { b, _ := json.Marshal(CreateBookRequest{Title: "Book1", Author: "Author1"}); return b }())))
	createBook(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/books",
		bytes.NewReader(func() []byte { b, _ := json.Marshal(CreateBookRequest{Title: "Book2", Author: "Author1"}); return b }())))

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	listBooks(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if len(books) != 2 {
		t.Errorf("Expected 2 books, got %d", len(books))
	}
}

func TestListBooksFilterByAuthor(t *testing.T) {
	setupTestDB(t)

	createBook(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/books",
		bytes.NewReader(func() []byte { b, _ := json.Marshal(CreateBookRequest{Title: "Book1", Author: "Author1"}); return b }())))
	createBook(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/books",
		bytes.NewReader(func() []byte { b, _ := json.Marshal(CreateBookRequest{Title: "Book2", Author: "Author2"}); return b }())))

	req := httptest.NewRequest(http.MethodGet, "/books?author=Author1", nil)
	w := httptest.NewRecorder()
	listBooks(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if len(books) != 1 {
		t.Errorf("Expected 1 book for Author1, got %d", len(books))
	}
}

func TestGetBook(t *testing.T) {
	setupTestDB(t)

	// Create a book first
	createBook(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/books",
		bytes.NewReader(func() []byte { b, _ := json.Marshal(CreateBookRequest{Title: "Test Book", Author: "Test Author", Year: 2020, ISBN: "12345"}); return b }())))

	req := httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w := httptest.NewRecorder()
	getBook(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if book.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got %s", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	setupTestDB(t)
	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()
	getBook(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	setupTestDB(t)

	createBook(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/books",
		bytes.NewReader(func() []byte { b, _ := json.Marshal(CreateBookRequest{Title: "Old Title", Author: "Old Author"}); return b }())))

	newTitle := "New Title"
	body, _ := json.Marshal(UpdateBookRequest{Title: &newTitle})
	req := httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewReader(body))
	w := httptest.NewRecorder()
	updateBook(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if book.Title != "New Title" {
		t.Errorf("Expected title 'New Title', got %s", book.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	setupTestDB(t)

	createBook(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/books",
		bytes.NewReader(func() []byte { b, _ := json.Marshal(CreateBookRequest{Title: "Delete Me", Author: "Test Author"}); return b }())))

	req := httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	w := httptest.NewRecorder()
	deleteBook(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status 204, got %d", w.Code)
	}

	// Verify it's gone
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w = httptest.NewRecorder()
	getBook(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 after delete, got %d", w.Code)
	}
}
