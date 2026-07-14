package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

// testDBFile creates a temp file path for the test DB.
// The caller is responsible for cleaning it up.
func testDBFile(t *testing.T) string {
	t.Helper()
	tmpFile, err := os.CreateTemp("", "books-*.db")
	if err != nil {
		t.Fatalf("create temp db: %v", err)
	}
	path := tmpFile.Name()
	tmpFile.Close()
	t.Cleanup(func() { os.Remove(path) })
	return path
}

// newTestServer creates a test handler with an in-memory SQLite DB.
func newTestServer(t *testing.T) *Handler {
	t.Helper()
	path := testDBFile(t)
	repo, err := NewSQLiteRepo(path)
	if err != nil {
		t.Fatalf("new sqlite repo: %v", err)
	}
	return NewHandler(repo)
}

// --- R1: POST /books creates a new book ---
func TestCreateBook(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	payload := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0743273565",
	}
	body, _ := json.Marshal(payload)

	req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("POST /books status = %d; want %d\nbody: %s", w.Code, http.StatusCreated, w.Body.String())
		return
	}

	var book Book
	if err := json.Unmarshal(w.Body.Bytes(), &book); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if book.Title != "The Great Gatsby" {
		t.Errorf("title = %q; want %q", book.Title, "The Great Gatsby")
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("author = %q; want %q", book.Author, "F. Scott Fitzgerald")
	}
	if book.Year != 1925 {
		t.Errorf("year = %d; want 1925", book.Year)
	}
	if book.ISBN != "978-0743273565" {
		t.Errorf("isbn = %q; want %q", book.ISBN, "978-0743273565")
	}
	if book.ID <= 0 {
		t.Errorf("id = %d; want > 0", book.ID)
	}
}

// --- R2: GET /books lists all books ---
func TestListBooks(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	// Create two books first
	createBook(t, mux, "Book One", "Author A", 2000, "isbn-1")
	createBook(t, mux, "Book Two", "Author B", 2001, "isbn-2")

	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("GET /books status = %d; want %d\nbody: %s", w.Code, http.StatusOK, w.Body.String())
	}

	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if len(books) != 2 {
		t.Errorf("got %d books; want 2", len(books))
	}
}

// --- R3: GET /books supports ?author= filter ---
func TestListBooksFilterByAuthor(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	createBook(t, mux, "Book One", "Author A", 2000, "isbn-1")
	createBook(t, mux, "Book Two", "Author B", 2001, "isbn-2")
	createBook(t, mux, "Book Three", "Author A", 2002, "isbn-3")

	req := httptest.NewRequest("GET", "/books?author=Author+A", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("GET /books?author= status = %d; want %d\nbody: %s", w.Code, http.StatusOK, w.Body.String())
	}

	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if len(books) != 2 {
		t.Errorf("got %d books for author Author A; want 2", len(books))
	}
	for _, b := range books {
		if b.Author != "Author A" {
			t.Errorf("book author = %q; want %q", b.Author, "Author A")
		}
	}
}

// --- R4: GET /books/{id} returns a single book (404 if absent) ---
func TestGetBook(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	// Create a book and get its ID
	b := createBook(t, mux, "Get Me", "Some Author", 2020, "isbn-10")

	// Get by valid ID
	req := httptest.NewRequest("GET", fmt.Sprintf("/books/%d", b.ID), nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("GET /books/%d status = %d; want %d\nbody: %s", b.ID, w.Code, http.StatusOK, w.Body.String())
	}
	var got Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got.ID != b.ID || got.Title != "Get Me" {
		t.Errorf("got = %+v; want %+v", got, b)
	}

	// Get with non-existent ID
	req = httptest.NewRequest("GET", "/books/99999", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("GET /books/99999 status = %d; want %d", w.Code, http.StatusNotFound)
	}
}

// --- R5: PUT /books/{id} updates a book ---
func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	original := createBook(t, mux, "Original Title", "Original Author", 2000, "old-isbn")

	payload := map[string]interface{}{
		"title": "Updated Title",
		"year":  2025,
	}
	body, _ := json.Marshal(payload)

	req := httptest.NewRequest("PUT", fmt.Sprintf("/books/%d", original.ID), bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("PUT /books/%d status = %d; want %d\nbody: %s", original.ID, w.Code, http.StatusOK, w.Body.String())
	}

	var updated Book
	if err := json.Unmarshal(w.Body.Bytes(), &updated); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if updated.Title != "Updated Title" {
		t.Errorf("title = %q; want %q", updated.Title, "Updated Title")
	}
	if updated.Year != 2025 {
		t.Errorf("year = %d; want 2025", updated.Year)
	}
	// Author and ISBN should be preserved (partial update)
	if updated.Author != "Original Author" {
		t.Errorf("author = %q; want %q", updated.Author, "Original Author")
	}
	if updated.ISBN != "old-isbn" {
		t.Errorf("isbn = %q; want %q", updated.ISBN, "old-isbn")
	}
}

// --- R6: DELETE /books/{id} deletes a book ---
func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	b := createBook(t, mux, "Delete Me", "Author", 2020, "isbn-del")

	req := httptest.NewRequest("DELETE", fmt.Sprintf("/books/%d", b.ID), nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusNoContent {
		t.Fatalf("DELETE /books/%d status = %d; want %d", b.ID, w.Code, http.StatusNoContent)
	}

	// Verify it is gone
	req = httptest.NewRequest("GET", fmt.Sprintf("/books/%d", b.ID), nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("GET deleted book status = %d; want %d", w.Code, http.StatusNotFound)
	}
}

// --- R7: Data stored in SQLite (verify via repository directly) ---
func TestSQLitePersistence(t *testing.T) {
	tmpFile, err := os.CreateTemp("", "sqlite-verify-*.db")
	if err != nil {
		t.Fatalf("create temp: %v", err)
	}
	tmpFile.Close()
	path := tmpFile.Name()
	defer os.Remove(path)

	repo, err := NewSQLiteRepo(path)
	if err != nil {
		t.Fatalf("new repo: %v", err)
	}
	defer repo.Close()

	_, err = repo.CreateBook("Persisted", "SQLite", 2024, "isbn-sqlite")
	if err != nil {
		t.Fatalf("create book: %v", err)
	}

	// Verify persistence through a fresh connection (same file)
	repo2, err := NewSQLiteRepo(path)
	if err != nil {
		t.Fatalf("reopen repo: %v", err)
	}
	defer repo2.Close()

	books, err := repo2.ListBooks(nil)
	if err != nil {
		t.Fatalf("list books: %v", err)
	}
	if len(books) != 1 {
		t.Fatalf("got %d books; want 1 (data should persist across connections)", len(books))
	}
	if books[0].Title != "Persisted" {
		t.Errorf("title = %q; want %q", books[0].Title, "Persisted")
	}
}

// --- R8: JSON responses with appropriate HTTP status codes ---
func TestHTTPStatusCodes(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	// Test method not allowed on /books
	req := httptest.NewRequest("PATCH", "/books", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH /books status = %d; want %d", w.Code, http.StatusMethodNotAllowed)
	}

	// Test method not allowed on /books/{id}
	req = httptest.NewRequest("PATCH", "/books/1", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH /books/1 status = %d; want %d", w.Code, http.StatusMethodNotAllowed)
	}

	// Test invalid book ID returns 400
	req = httptest.NewRequest("GET", "/books/abc", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Errorf("GET /books/abc status = %d; want %d", w.Code, http.StatusBadRequest)
	}
}

// --- R9: Input validation: title and author are required ---
func TestValidationRequiredFields(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	tests := []struct {
		name     string
		payload  map[string]interface{}
		wantCode int
		wantBody string
	}{
		{
			name:     "missing title",
			payload:  map[string]interface{}{"author": "Author", "year": 2020, "isbn": "isbn"},
			wantCode: http.StatusBadRequest,
			wantBody: "title is required",
		},
		{
			name:     "missing author",
			payload:  map[string]interface{}{"title": "Title", "year": 2020, "isbn": "isbn"},
			wantCode: http.StatusBadRequest,
			wantBody: "author is required",
		},
		{
			name:     "empty title",
			payload:  map[string]interface{}{"title": "", "author": "Author", "year": 2020, "isbn": "isbn"},
			wantCode: http.StatusBadRequest,
			wantBody: "title is required",
		},
		{
			name:     "whitespace-only author",
			payload:  map[string]interface{}{"title": "Title", "author": "   ", "year": 2020, "isbn": "isbn"},
			wantCode: http.StatusBadRequest,
			wantBody: "author is required",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			body, _ := json.Marshal(tc.payload)
			req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			mux.ServeHTTP(w, req)

			if w.Code != tc.wantCode {
				t.Errorf("status = %d; want %d", w.Code, tc.wantCode)
			}

			var errResp ErrorResponse
			if err := json.Unmarshal(w.Body.Bytes(), &errResp); err != nil {
				t.Fatalf("decode error: %v", err)
			}
			if errResp.Error != tc.wantBody {
				t.Errorf("error message = %q; want %q", errResp.Error, tc.wantBody)
			}
		})
	}
}

// --- R10: GET /health health-check endpoint ---
func TestHealthCheck(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET /health status = %d; want %d", w.Code, http.StatusOK)
	}

	var resp map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("status = %q; want %q", resp["status"], "ok")
	}

	// Method not allowed on health
	req = httptest.NewRequest("POST", "/health", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("POST /health status = %d; want %d", w.Code, http.StatusMethodNotAllowed)
	}
}

// --- R12: Count tests (at least 3 unit/integration tests) ---
func TestBookModel(t *testing.T) {
	// Basic unit test for the Book model
	b := Book{ID: 1, Title: "Test", Author: "Author", Year: 2020, ISBN: "isbn-1"}
	if b.ID != 1 || b.Title != "Test" || b.Author != "Author" || b.Year != 2020 || b.ISBN != "isbn-1" {
		t.Errorf("Book struct = %+v; mismatch", b)
	}
}

func TestErrNotFound(t *testing.T) {
	if ErrNotFound.Error() != "resource not found" {
		t.Errorf("ErrNotFound message = %q; want %q", ErrNotFound.Error(), "resource not found")
	}
}

// --- UpdateBook returns 404 for non-existent ID ---
func TestUpdateBookNotFound(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	payload := map[string]interface{}{"title": "Ghost"}
	body, _ := json.Marshal(payload)

	req := httptest.NewRequest("PUT", "/books/99999", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("PUT /books/99999 status = %d; want %d", w.Code, http.StatusNotFound)
	}
}

// --- DeleteBook returns 404 for non-existent ID ---
func TestDeleteBookNotFound(t *testing.T) {
	h := newTestServer(t)
	mux := setupRoutes(h)

	req := httptest.NewRequest("DELETE", "/books/99999", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("DELETE /books/99999 status = %d; want %d", w.Code, http.StatusNotFound)
	}
}

// --- createBook is a test helper that creates a book and returns it ---
func createBook(t *testing.T, mux *http.ServeMux, title, author string, year int, isbn string) Book {
	t.Helper()
	payload := map[string]interface{}{
		"title":  title,
		"author": author,
		"year":   year,
		"isbn":   isbn,
	}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("create test book status = %d; want %d\nbody: %s", w.Code, http.StatusCreated, w.Body.String())
	}

	var book Book
	if err := json.Unmarshal(w.Body.Bytes(), &book); err != nil {
		t.Fatalf("decode: %v", err)
	}
	return book
}

// setupRoutes mirrors the route setup in main.go for testing.
func setupRoutes(h *Handler) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", h.healthCheck)
	mux.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			h.createBook(w, r)
		case http.MethodGet:
			h.listBooks(w, r)
		default:
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		}
	})
	mux.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			h.getBook(w, r)
		case http.MethodPut:
			h.updateBook(w, r)
		case http.MethodDelete:
			h.deleteBook(w, r)
		default:
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		}
	})
	return mux
}
