package main

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestMain(m *testing.M) {
	// Use a test database file
	dbFile = "test_books.db"
	if err := initDB(); err != nil {
		log.Fatalf("failed to initialize test database: %v", err)
	}
	code := m.Run()
	db.Close()
	os.Remove(dbFile)
	os.Exit(code)
}

func TestHealthEndpoint(t *testing.T) {
	resetDB()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got %s", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	resetDB()
	body := `{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got %s", book.Title)
	}
	if book.ID != 1 {
		t.Errorf("expected ID 1, got %d", book.ID)
	}
}

func TestCreateBookMissingTitle(t *testing.T) {
	resetDB()
	body := `{"author":"Test Author","year":2020,"isbn":"123"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	resetDB()
	// Create a book first
	body := `{"title":"Clean Code","author":"Robert Martin","year":2008,"isbn":"978-0132350884"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksHandler(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %d", w.Code)
	}

	// List all books
	req = httptest.NewRequest(http.MethodGet, "/books", nil)
	w = httptest.NewRecorder()
	booksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(books) != 1 {
		t.Errorf("expected 1 book, got %d", len(books))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	resetDB()
	// Create two books
	body1 := `{"title":"Book A","author":"Author X","year":2020,"isbn":"isbn-a"}`
	body2 := `{"title":"Book B","author":"Author Y","year":2021,"isbn":"isbn-b"}`

	req1 := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body1))
	req1.Header.Set("Content-Type", "application/json")
	w1 := httptest.NewRecorder()
	booksHandler(w1, req1)
	if w1.Code != http.StatusCreated {
		t.Fatalf("create book A failed: %d", w1.Code)
	}

	req2 := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body2))
	req2.Header.Set("Content-Type", "application/json")
	w2 := httptest.NewRecorder()
	booksHandler(w2, req2)
	if w2.Code != http.StatusCreated {
		t.Fatalf("create book B failed: %d", w2.Code)
	}

	// Filter by author
	req := httptest.NewRequest(http.MethodGet, "/books?author=Author+X", nil)
	w := httptest.NewRecorder()
	booksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(books) != 1 {
		t.Errorf("expected 1 book, got %d", len(books))
	}
	if books[0].Title != "Book A" {
		t.Errorf("expected 'Book A', got %s", books[0].Title)
	}
}

func TestGetBook(t *testing.T) {
	resetDB()
	// Create a book
	body := `{"title":"Test Book","author":"Test Author","year":2023,"isbn":"test-isbn"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksHandler(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %d", w.Code)
	}

	// Get the book
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w = httptest.NewRecorder()
	bookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if book.Title != "Test Book" {
		t.Errorf("expected 'Test Book', got %s", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	resetDB()
	req := httptest.NewRequest(http.MethodGet, "/books/9999", nil)
	w := httptest.NewRecorder()
	bookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	resetDB()
	// Create a book
	body := `{"title":"Old Title","author":"Old Author","year":2020,"isbn":"update-isbn"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksHandler(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %d", w.Code)
	}

	// Update the book
	body = `{"title":"New Title","author":"New Author","year":2024,"isbn":"new-isbn"}`
	req = httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	bookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if book.Title != "New Title" {
		t.Errorf("expected 'New Title', got %s", book.Title)
	}
	if book.Author != "New Author" {
		t.Errorf("expected 'New Author', got %s", book.Author)
	}
}

func TestDeleteBook(t *testing.T) {
	resetDB()
	// Create a book
	body := `{"title":"Delete Me","author":"Author","year":2023,"isbn":"delete-isbn"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksHandler(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %d", w.Code)
	}

	// Delete the book
	req = httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	w = httptest.NewRecorder()
	bookHandler(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("expected status 204, got %d", w.Code)
	}

	// Verify it's gone
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w = httptest.NewRecorder()
	bookHandler(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", w.Code)
	}
}
