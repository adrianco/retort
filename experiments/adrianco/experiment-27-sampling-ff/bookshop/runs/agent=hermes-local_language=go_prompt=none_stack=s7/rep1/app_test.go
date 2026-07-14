package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func setupTestServer(t *testing.T) *Server {
	t.Helper()
	// Use in-memory SQLite for testing
	db, err := sql.Open("sqlite3", ":memory:?cache=shared")
	if err != nil {
		t.Fatalf("Failed to open test database: %v", err)
	}

	store := &BookStore{db: db}
	if err := store.initializeDB(); err != nil {
		t.Fatalf("Failed to initialize test database: %v", err)
	}

	server := NewServer(store, "8080")
	t.Cleanup(func() {
		store.Close()
	})
	return server
}

// createTestBook creates a book in the server and returns its ID
func createTestBook(t *testing.T, server *Server, book Book) int {
	t.Helper()
	body, err := json.Marshal(book)
	if err != nil {
		t.Fatal(err)
	}
	req, _ := http.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	server.booksHandler(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("create test book: expected %d, got %d", http.StatusCreated, rr.Code)
	}

	var created Book
	json.NewDecoder(rr.Body).Decode(&created)
	return created.ID
}

func TestHealthEndpoint(t *testing.T) {
	server := setupTestServer(t)

	req, err := http.NewRequest(http.MethodGet, "/health", nil)
	if err != nil {
		t.Fatal(err)
	}

	rr := httptest.NewRecorder()
	handler := http.HandlerFunc(server.healthHandler)
	handler.ServeHTTP(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("health endpoint: expected status %d, got %d", http.StatusOK, status)
	}

	var response map[string]string
	if err := json.NewDecoder(rr.Body).Decode(&response); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if response["status"] != "ok" {
		t.Errorf("health endpoint: expected status 'ok', got '%s'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	server := setupTestServer(t)

	book := Book{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}

	body, err := json.Marshal(book)
	if err != nil {
		t.Fatal(err)
	}

	req, err := http.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	server.booksHandler(rr, req)

	if status := rr.Code; status != http.StatusCreated {
		t.Errorf("create book: expected status %d, got %d", http.StatusCreated, status)
	}

	var createdBook Book
	if err := json.NewDecoder(rr.Body).Decode(&createdBook); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if createdBook.Title != book.Title {
		t.Errorf("create book: expected title '%s', got '%s'", book.Title, createdBook.Title)
	}
	if createdBook.Author != book.Author {
		t.Errorf("create book: expected author '%s', got '%s'", book.Author, createdBook.Author)
	}
	if createdBook.ID == 0 {
		t.Error("create book: expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	server := setupTestServer(t)

	tests := []struct {
		name     string
		book     Book
		expected int
	}{
		{
			name:     "missing title",
			book:     Book{Title: "", Author: "Author", Year: 2020, ISBN: "123"},
			expected: http.StatusBadRequest,
		},
		{
			name:     "missing author",
			book:     Book{Title: "Title", Author: "", Year: 2020, ISBN: "123"},
			expected: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body, _ := json.Marshal(tt.book)
			req, _ := http.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			rr := httptest.NewRecorder()
			server.booksHandler(rr, req)

			if status := rr.Code; status != tt.expected {
				t.Errorf("validation: expected status %d, got %d", tt.expected, status)
			}
		})
	}
}

func TestGetBook(t *testing.T) {
	server := setupTestServer(t)

	// First create a book
	bookID := createTestBook(t, server, Book{
		Title:  "1984",
		Author: "George Orwell",
		Year:   1949,
		ISBN:   "978-0451524935",
	})

	// Now get the book
	req, _ := http.NewRequest(http.MethodGet, "/books/"+strconv.Itoa(bookID), nil)
	rr := httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("get book: expected status %d, got %d", http.StatusOK, status)
	}

	var gotBook Book
	json.NewDecoder(rr.Body).Decode(&gotBook)

	if gotBook.Title != "1984" {
		t.Errorf("get book: expected title '1984', got '%s'", gotBook.Title)
	}
	if gotBook.Author != "George Orwell" {
		t.Errorf("get book: expected author 'George Orwell', got '%s'", gotBook.Author)
	}
}

func TestGetBookNotFound(t *testing.T) {
	server := setupTestServer(t)

	req, _ := http.NewRequest(http.MethodGet, "/books/999", nil)
	rr := httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusNotFound {
		t.Errorf("get book not found: expected status %d, got %d", http.StatusNotFound, status)
	}
}

func TestListBooks(t *testing.T) {
	server := setupTestServer(t)

	// Create multiple books
	books := []Book{
		{Title: "Book A", Author: "Author X", Year: 2020, ISBN: "111"},
		{Title: "Book B", Author: "Author X", Year: 2021, ISBN: "222"},
		{Title: "Book C", Author: "Author Y", Year: 2022, ISBN: "333"},
	}
	for _, b := range books {
		createTestBook(t, server, b)
	}

	// List all
	req, _ := http.NewRequest(http.MethodGet, "/books", nil)
	rr := httptest.NewRecorder()
	server.booksHandler(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("list books: expected status %d, got %d", http.StatusOK, status)
	}

	var gotBooks []Book
	json.NewDecoder(rr.Body).Decode(&gotBooks)

	if len(gotBooks) != 3 {
		t.Errorf("list books: expected 3 books, got %d", len(gotBooks))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	server := setupTestServer(t)

	// Create multiple books
	books := []Book{
		{Title: "Book A", Author: "Author X", Year: 2020, ISBN: "111"},
		{Title: "Book B", Author: "Author X", Year: 2021, ISBN: "222"},
		{Title: "Book C", Author: "Author Y", Year: 2022, ISBN: "333"},
	}
	for _, b := range books {
		createTestBook(t, server, b)
	}

	// Filter by author
	req, _ := http.NewRequest(http.MethodGet, "/books?author=Author+X", nil)
	rr := httptest.NewRecorder()
	server.booksHandler(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("list books by author: expected status %d, got %d", http.StatusOK, status)
	}

	var gotBooks []Book
	json.NewDecoder(rr.Body).Decode(&gotBooks)

	if len(gotBooks) != 2 {
		t.Errorf("list books by author: expected 2 books, got %d", len(gotBooks))
	}
	for _, b := range gotBooks {
		if b.Author != "Author X" {
			t.Errorf("list books by author: expected author 'Author X', got '%s'", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	server := setupTestServer(t)

	// Create a book first
	bookID := createTestBook(t, server, Book{Title: "Original", Author: "Author", Year: 2000, ISBN: "000"})

	// Update the book
	updated := Book{Title: "Updated", Author: "Updated Author", Year: 2023, ISBN: "999"}
	body, _ := json.Marshal(updated)
	req, _ := http.NewRequest(http.MethodPut, "/books/"+strconv.Itoa(bookID), bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("update book: expected status %d, got %d", http.StatusOK, status)
	}

	var gotBook Book
	json.NewDecoder(rr.Body).Decode(&gotBook)

	if gotBook.Title != "Updated" {
		t.Errorf("update book: expected title 'Updated', got '%s'", gotBook.Title)
	}
	if gotBook.Author != "Updated Author" {
		t.Errorf("update book: expected author 'Updated Author', got '%s'", gotBook.Author)
	}
}

func TestUpdateBookValidation(t *testing.T) {
	server := setupTestServer(t)

	// Create a book first
	bookID := createTestBook(t, server, Book{Title: "Original", Author: "Author", Year: 2000, ISBN: "000"})

	// Try to update with empty title
	invalid := Book{Title: "", Author: "Updated Author", Year: 2023, ISBN: "999"}
	body, _ := json.Marshal(invalid)
	req, _ := http.NewRequest(http.MethodPut, "/books/"+strconv.Itoa(bookID), bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusBadRequest {
		t.Errorf("update book validation: expected status %d, got %d", http.StatusBadRequest, status)
	}
}

func TestDeleteBook(t *testing.T) {
	server := setupTestServer(t)

	// Create a book first
	bookID := createTestBook(t, server, Book{Title: "ToDelete", Author: "Author", Year: 2020, ISBN: "111"})

	// Delete the book
	req, _ := http.NewRequest(http.MethodDelete, "/books/"+strconv.Itoa(bookID), nil)
	rr := httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusNoContent {
		t.Errorf("delete book: expected status %d, got %d", http.StatusNoContent, status)
	}

	// Verify it's deleted
	req, _ = http.NewRequest(http.MethodGet, "/books/"+strconv.Itoa(bookID), nil)
	rr = httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusNotFound {
		t.Errorf("delete book: expected status %d after deletion, got %d", http.StatusNotFound, status)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	server := setupTestServer(t)

	req, _ := http.NewRequest(http.MethodDelete, "/books/999", nil)
	rr := httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusNotFound {
		t.Errorf("delete book not found: expected status %d, got %d", http.StatusNotFound, status)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	server := setupTestServer(t)

	// Create a book so GET /books/1 can succeed
	bookID := createTestBook(t, server, Book{Title: "Test", Author: "Test", Year: 2020, ISBN: "000"})

	tests := []struct {
		name     string
		method   string
		path     string
		expected int
		handler  func(http.ResponseWriter, *http.Request)
	}{
		{
			name:     "POST /health",
			method:   http.MethodPost,
			path:     "/health",
			expected: http.StatusMethodNotAllowed,
			handler:  server.healthHandler,
		},
		{
			name:     "DELETE /books",
			method:   http.MethodDelete,
			path:     "/books",
			expected: http.StatusMethodNotAllowed,
			handler:  server.booksHandler,
		},
		{
			name:     "GET /books/1 (should succeed)",
			method:   http.MethodGet,
			path:     "/books/" + strconv.Itoa(bookID),
			expected: http.StatusOK,
			handler:  server.bookByIDHandler,
		},
		{
			name:     "PATCH /books/1",
			method:   "PATCH",
			path:     "/books/" + strconv.Itoa(bookID),
			expected: http.StatusMethodNotAllowed,
			handler:  server.bookByIDHandler,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req, _ := http.NewRequest(tt.method, tt.path, nil)
			rr := httptest.NewRecorder()
			tt.handler(rr, req)

			if status := rr.Code; status != tt.expected {
				t.Errorf("method check: expected status %d, got %d", tt.expected, status)
			}
		})
	}
}

func TestInvalidBookID(t *testing.T) {
	server := setupTestServer(t)

	req, _ := http.NewRequest(http.MethodGet, "/books/abc", nil)
	rr := httptest.NewRecorder()
	server.bookByIDHandler(rr, req)

	if status := rr.Code; status != http.StatusBadRequest {
		t.Errorf("invalid book ID: expected status %d, got %d", http.StatusBadRequest, status)
	}
}

func TestEmptyBookList(t *testing.T) {
	server := setupTestServer(t)

	req, _ := http.NewRequest(http.MethodGet, "/books", nil)
	rr := httptest.NewRecorder()
	server.booksHandler(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("empty list: expected status %d, got %d", http.StatusOK, status)
	}

	var books []Book
	json.NewDecoder(rr.Body).Decode(&books)

	if len(books) != 0 {
		t.Errorf("empty list: expected 0 books, got %d", len(books))
	}
}

func TestMain(m *testing.M) {
	// Clean up any existing test database
	os.Remove("test_books.db")
	os.Exit(m.Run())
}
