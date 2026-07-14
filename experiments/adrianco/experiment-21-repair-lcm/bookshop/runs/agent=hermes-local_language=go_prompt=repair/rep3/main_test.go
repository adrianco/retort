package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
)

func setupTestStore(t *testing.T) *BookStore {
	t.Helper()
	// Use a unique temp file per test run so each test gets a fresh DB
	dbPath := fmt.Sprintf("/tmp/book-api-test-%d.db", time.Now().UnixNano())
	store, err := NewBookStore(dbPath)
	if err != nil {
		t.Fatalf("Failed to create test store: %v", err)
	}
	// Clean up the test DB file after the test
	t.Cleanup(func() { os.Remove(dbPath) })
	return store
}

func seedTestBooks(t *testing.T, store *BookStore) {
	t.Helper()
	books := []Book{
		{Title: "1984", Author: "George Orwell", Year: 1949, ISBN: "978-0451524935"},
		{Title: "Animal Farm", Author: "George Orwell", Year: 1945, ISBN: "978-0451526342"},
		{Title: "To Kill a Mockingbird", Author: "Harper Lee", Year: 1960, ISBN: "978-0061120084"},
	}
	for _, b := range books {
		_, err := store.CreateBook(b.Title, b.Author, b.Year, b.ISBN)
		if err != nil {
			t.Fatalf("Failed to seed book %s: %v", b.Title, err)
		}
	}
}

// TestCreateBook_Valid tests POST /books with valid data
func TestCreateBook_Valid(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()

	book := Book{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}
	body, _ := json.Marshal(book)

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d. Body: %s", http.StatusCreated, w.Code, w.Body.String())
	}

	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	if created.ID == 0 {
		t.Error("Expected non-zero ID for created book")
	}
	if created.Title != book.Title {
		t.Errorf("Expected title %q, got %q", book.Title, created.Title)
	}
	if created.Author != book.Author {
		t.Errorf("Expected author %q, got %q", book.Author, created.Author)
	}
}

// TestCreateBook_Invalid tests POST /books with missing required fields
func TestCreateBook_Invalid(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()

	tests := []struct {
		name     string
		book     Book
		expected int
	}{
		{
			name:     "missing title",
			book:     Book{Author: "Some Author", Year: 2000, ISBN: "123"},
			expected: http.StatusBadRequest,
		},
		{
			name:     "missing author",
			book:     Book{Title: "Some Book", Year: 2000, ISBN: "123"},
			expected: http.StatusBadRequest,
		},
		{
			name:     "missing year",
			book:     Book{Title: "Some Book", Author: "Some Author", ISBN: "123"},
			expected: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body, _ := json.Marshal(tt.book)
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()

			store.ServeHTTP(w, req)

			if w.Code != tt.expected {
				t.Errorf("Expected status %d, got %d. Body: %s", tt.expected, w.Code, w.Body.String())
			}

			var resp map[string]string
			json.Unmarshal(w.Body.Bytes(), &resp)
			if resp["error"] == "" {
				t.Error("Expected error message in response")
			}
		})
	}
}

// TestGetBookByID tests GET /books/{id}
func TestGetBookByID(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()
	seedTestBooks(t, store)

	book, err := store.GetBookByID(1)
	if err != nil {
		t.Fatalf("GetBookByID returned error: %v", err)
	}
	if book == nil {
		t.Fatal("Expected book, got nil")
	}
	if book.Title != "1984" {
		t.Errorf("Expected title '1984', got %q", book.Title)
	}
}

// TestGetBookByID_NotFound tests GET /books/{id} for non-existent book
func TestGetBookByID_NotFound(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d. Body: %s", http.StatusNotFound, w.Code, w.Body.String())
	}
}

// TestListBooks tests GET /books
func TestListBooks(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()
	seedTestBooks(t, store)

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusOK, w.Code, w.Body.String())
	}

	var books []*Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatalf("Failed to unmarshal books: %v", err)
	}

	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}
}

// TestListBooks_AuthorFilter tests GET /books?author=
func TestListBooks_AuthorFilter(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()
	seedTestBooks(t, store)

	req := httptest.NewRequest(http.MethodGet, "/books?author=George+Orwell", nil)
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusOK, w.Code, w.Body.String())
	}

	var books []*Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatalf("Failed to unmarshal books: %v", err)
	}

	if len(books) != 2 {
		t.Errorf("Expected 2 Orwell books, got %d", len(books))
	}

	for _, b := range books {
		if b.Author != "George Orwell" {
			t.Errorf("Expected author 'George Orwell', got %q", b.Author)
		}
	}
}

// TestUpdateBook tests PUT /books/{id}
func TestUpdateBook(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()
	seedTestBooks(t, store)

	updatedBook := Book{
		Title:  "1984 (Updated)",
		Author: "George Orwell",
		Year:   1949,
		ISBN:   "978-0451524935",
	}
	body, _ := json.Marshal(updatedBook)

	req := httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusOK, w.Code, w.Body.String())
	}

	var result Book
	if err := json.Unmarshal(w.Body.Bytes(), &result); err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	if result.Title != "1984 (Updated)" {
		t.Errorf("Expected title '1984 (Updated)', got %q", result.Title)
	}

	// Verify the update persisted
	retrieved, err := store.GetBookByID(1)
	if err != nil {
		t.Fatalf("Failed to get updated book: %v", err)
	}
	if retrieved.Title != "1984 (Updated)" {
		t.Errorf("Persisted title is wrong: expected '1984 (Updated)', got %q", retrieved.Title)
	}
}

// TestDeleteBook tests DELETE /books/{id}
func TestDeleteBook(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()
	seedTestBooks(t, store)

	req := httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d. Body: %s", http.StatusNoContent, w.Code, w.Body.String())
	}

	// Verify deletion
	book, err := store.GetBookByID(1)
	if err != nil {
		t.Fatalf("GetBookByID returned error: %v", err)
	}
	if book != nil {
		t.Errorf("Expected nil book after deletion, got %v", book)
	}

	// Remaining books should still be there
	req = httptest.NewRequest(http.MethodGet, "/books", nil)
	w = httptest.NewRecorder()
	store.ServeHTTP(w, req)

	var books []*Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 2 {
		t.Errorf("Expected 2 books remaining, got %d", len(books))
	}
}

// TestHealthCheck tests GET /health
func TestHealthCheck(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()

	mux := http.NewServeMux()
	mux.Handle("/books", store)
	mux.HandleFunc("/books/", store.ServeHTTP)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		writeJSON(w, map[string]string{"status": "healthy"}, http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d. Body: %s", http.StatusOK, w.Code, w.Body.String())
	}

	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got %q", resp["status"])
	}
}

// TestDuplicateISBN tests that duplicate ISBN is rejected
func TestDuplicateISBN(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()

	book1 := Book{Title: "Book One", Author: "Author One", Year: 2020, ISBN: "123-456"}
	body1, _ := json.Marshal(book1)

	req1 := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body1))
	req1.Header.Set("Content-Type", "application/json")
	w1 := httptest.NewRecorder()
	store.ServeHTTP(w1, req1)

	if w1.Code != http.StatusCreated {
		t.Fatalf("First insert should succeed, got status %d", w1.Code)
	}

	book2 := Book{Title: "Book Two", Author: "Author Two", Year: 2021, ISBN: "123-456"}
	body2, _ := json.Marshal(book2)

	req2 := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body2))
	req2.Header.Set("Content-Type", "application/json")
	w2 := httptest.NewRecorder()
	store.ServeHTTP(w2, req2)

	if w2.Code != http.StatusConflict {
		t.Errorf("Expected status %d for duplicate ISBN, got %d. Body: %s", http.StatusConflict, w2.Code, w2.Body.String())
	}
}

// TestListBooks_Empty tests GET /books with no books
func TestListBooks_Empty(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusOK, w.Code, w.Body.String())
	}

	var books []*Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatalf("Failed to unmarshal books: %v", err)
	}

	if len(books) != 0 {
		t.Errorf("Expected 0 books, got %d", len(books))
	}
}

// TestDeleteNonExistentBook tests deleting a book that doesn't exist
func TestDeleteNonExistentBook(t *testing.T) {
	store := setupTestStore(t)
	defer store.Close()

	req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
	w := httptest.NewRecorder()

	store.ServeHTTP(w, req)

	// No error for deleting non-existent book, just no content
	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d", http.StatusNoContent, w.Code)
	}
}
