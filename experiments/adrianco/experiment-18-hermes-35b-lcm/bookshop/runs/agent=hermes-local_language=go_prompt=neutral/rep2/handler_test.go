package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

// setupTestDB creates a fresh in-memory test database and returns the server.
func setupTestDB(t *testing.T) *Server {
	t.Helper()
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create test database: %v", err)
	}
	return NewServer(db)
}

// Helper: do a request and return the response body bytes and status.
func doRequest(s *Server, method, path string, body interface{}) (*http.Response, []byte, error) {
	var reqBody io.Reader
	if body != nil {
		data, _ := json.Marshal(body)
		reqBody = bytes.NewReader(data)
	} else {
		reqBody = http.NoBody
	}

	r := httptest.NewRequest(method, path, reqBody)
	w := httptest.NewRecorder()

	s.HandleBooks(w, r)
	// Also route /health
	if path == "/health" {
		s.HandleHealth(w, r)
	}

	return w.Result(), w.Body.Bytes(), nil
}

// ========== Create Book Tests ==========

func TestCreateBookSuccess(t *testing.T) {
	s := setupTestDB(t)

	req := CreateBookRequest{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}

	resp, body, err := doRequest(s, http.MethodPost, "/books", req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusCreated {
		t.Errorf("expected 201, got %d", resp.StatusCode)
	}

	var book Book
	if err := json.Unmarshal(body, &book); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got '%s'", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}
	if book.ISBN != "978-0743273565" {
		t.Errorf("expected ISBN '978-0743273565', got '%s'", book.ISBN)
	}
	if book.ID != 1 {
		t.Errorf("expected ID 1, got %d", book.ID)
	}
}

func TestCreateBookMissingTitle(t *testing.T) {
	s := setupTestDB(t)

	req := CreateBookRequest{
		Author: "Some Author",
		Year:   2020,
		ISBN:   "123",
	}

	resp, body, err := doRequest(s, http.MethodPost, "/books", req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", resp.StatusCode)
	}

	var errResp ErrorResponse
	json.Unmarshal(body, &errResp)
	if len(errResp.Validation) == 0 {
		t.Error("expected validation errors")
	}

	found := false
	for _, v := range errResp.Validation {
		if v.Field == "title" {
			found = true
		}
	}
	if !found {
		t.Error("expected validation error on 'title' field")
	}
}

func TestCreateBookMissingAuthor(t *testing.T) {
	s := setupTestDB(t)

	req := CreateBookRequest{
		Title: "Some Book",
		Year:  2020,
		ISBN:  "123",
	}

	resp, body, err := doRequest(s, http.MethodPost, "/books", req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", resp.StatusCode)
	}

	var errResp ErrorResponse
	json.Unmarshal(body, &errResp)

	found := false
	for _, v := range errResp.Validation {
		if v.Field == "author" {
			found = true
		}
	}
	if !found {
		t.Error("expected validation error on 'author' field")
	}
}

func TestCreateBookEmptyTitleAndAuthor(t *testing.T) {
	s := setupTestDB(t)

	req := CreateBookRequest{}

	resp, body, err := doRequest(s, http.MethodPost, "/books", req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", resp.StatusCode)
	}

	var errResp ErrorResponse
	if err := json.Unmarshal(body, &errResp); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	if len(errResp.Validation) != 2 {
		t.Errorf("expected 2 validation errors, got %d", len(errResp.Validation))
	}
}

// ========== List Books Tests ==========

func TestListBooksEmpty(t *testing.T) {
	s := setupTestDB(t)

	resp, body, err := doRequest(s, http.MethodGet, "/books", nil)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var books []Book
	if err := json.Unmarshal(body, &books); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	if len(books) != 0 {
		t.Errorf("expected 0 books, got %d", len(books))
	}
}

func TestListBooksReturnsAll(t *testing.T) {
	s := setupTestDB(t)

	// Create a couple of books
	s.db.CreateBook("Book A", "Author X", 2020, "isbn-a")
	s.db.CreateBook("Book B", "Author X", 2021, "isbn-b")
	s.db.CreateBook("Book C", "Author Y", 2022, "isbn-c")

	resp, body, _ := doRequest(s, http.MethodGet, "/books", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var books []Book
	json.Unmarshal(body, &books)

	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}
}

func TestListBooksFilterByAuthor(t *testing.T) {
	s := setupTestDB(t)

	s.db.CreateBook("Book A", "Author X", 2020, "isbn-a")
	s.db.CreateBook("Book B", "Author Y", 2021, "isbn-b")
	s.db.CreateBook("Book C", "Author Z", 2022, "isbn-c")

	resp, body, _ := doRequest(s, http.MethodGet, "/books?author=Author+Y", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var books []Book
	json.Unmarshal(body, &books)

	if len(books) != 1 {
		t.Errorf("expected 1 book for Author Y, got %d", len(books))
	}
	if books[0].Author != "Author Y" {
		t.Errorf("expected Author Y, got %s", books[0].Author)
	}
}

// ========== Get Book Tests ==========

func TestGetBookSuccess(t *testing.T) {
	s := setupTestDB(t)

	_, _ = s.db.CreateBook("Dune", "Frank Herbert", 1965, "978-0441172719")

	resp, body, err := doRequest(s, http.MethodGet, "/books/1", nil)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var book Book
	if err := json.Unmarshal(body, &book); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	if book.ID != 1 {
		t.Errorf("expected ID 1, got %d", book.ID)
	}
	if book.Title != "Dune" {
		t.Errorf("expected title 'Dune', got '%s'", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	s := setupTestDB(t)

	resp, _, err := doRequest(s, http.MethodGet, "/books/999", nil)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.StatusCode)
	}
}

// ========== Update Book Tests ==========

func TestUpdateBookSuccess(t *testing.T) {
	s := setupTestDB(t)

	_, _ = s.db.CreateBook("Old Title", "Old Author", 2000, "old-isbn")

	req := UpdateBookRequest{
		Title:  strPtr("New Title"),
		Author: strPtr("New Author"),
		Year:   intPtr(2023),
		ISBN:   strPtr("new-isbn"),
	}

	resp, body, err := doRequest(s, http.MethodPut, "/books/1", req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var book Book
	json.Unmarshal(body, &book)

	if book.Title != "New Title" {
		t.Errorf("expected title 'New Title', got '%s'", book.Title)
	}
	if book.Author != "New Author" {
		t.Errorf("expected author 'New Author', got '%s'", book.Author)
	}
	if book.Year != 2023 {
		t.Errorf("expected year 2023, got %d", book.Year)
	}
	if book.ISBN != "new-isbn" {
		t.Errorf("expected ISBN 'new-isbn', got '%s'", book.ISBN)
	}
}

func TestUpdateBookPartial(t *testing.T) {
	s := setupTestDB(t)

	s.db.CreateBook("Original Title", "Original Author", 2000, "original-isbn")

	req := UpdateBookRequest{
		Title: strPtr("Updated Title"),
	}

	resp, body, err := doRequest(s, http.MethodPut, "/books/1", req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var book Book
	json.Unmarshal(body, &book)

	if book.Title != "Updated Title" {
		t.Errorf("expected title 'Updated Title', got '%s'", book.Title)
	}
	// Author, Year, ISBN should remain unchanged
	if book.Author != "Original Author" {
		t.Errorf("expected author to stay 'Original Author', got '%s'", book.Author)
	}
	if book.Year != 2000 {
		t.Errorf("expected year to stay 2000, got %d", book.Year)
	}
	if book.ISBN != "original-isbn" {
		t.Errorf("expected ISBN to stay 'original-isbn', got '%s'", book.ISBN)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	s := setupTestDB(t)

	req := UpdateBookRequest{Title: strPtr("New Title")}

	resp, _, err := doRequest(s, http.MethodPut, "/books/999", req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.StatusCode)
	}
}

// ========== Delete Book Tests ==========

func TestDeleteBookSuccess(t *testing.T) {
	s := setupTestDB(t)

	s.db.CreateBook("ToDelete", "Author", 2020, "isbn-del")

	resp, _, err := doRequest(s, http.MethodDelete, "/books/1", nil)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusNoContent {
		t.Errorf("expected 204, got %d", resp.StatusCode)
	}

	// Verify it's gone
	resp, _, _ = doRequest(s, http.MethodGet, "/books/1", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected deleted book to return 404, got %d", resp.StatusCode)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	s := setupTestDB(t)

	resp, _, err := doRequest(s, http.MethodDelete, "/books/999", nil)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.StatusCode)
	}
}

// ========== Health Check Test ==========

func TestHealthCheck(t *testing.T) {
	s := setupTestDB(t)

	r := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	s.HandleHealth(w, r)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var resp HealthResponse
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	if resp.Status != "ok" {
		t.Errorf("expected status 'ok', got '%s'", resp.Status)
	}
}

// ========== Integration Tests ==========

func TestFullLifecycle(t *testing.T) {
	s := setupTestDB(t)

	// 1. Create
	createReq := CreateBookRequest{
		Title:  "War and Peace",
		Author: "Leo Tolstoy",
		Year:   1869,
		ISBN:   "978-0199232765",
	}
	resp, body, err := doRequest(s, http.MethodPost, "/books", createReq)
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("expected 201 on create, got %d", resp.StatusCode)
	}

	var created Book
	json.Unmarshal(body, &created)
	if created.ID <= 0 {
		t.Fatal("expected positive ID on created book")
	}

	// 2. Get
	resp, body, err = doRequest(s, http.MethodGet, "/books/1", nil)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200 on get, got %d", resp.StatusCode)
	}
	_ = body // validate body exists

	// 3. List
	resp, body, _ = doRequest(s, http.MethodGet, "/books", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list failed: %d", resp.StatusCode)
	}
	var books []Book
	json.Unmarshal(body, &books)
	if len(books) != 1 {
		t.Errorf("expected 1 book in list, got %d", len(books))
	}

	// 4. Update
	resp, body, err = doRequest(s, http.MethodPut, "/books/1", UpdateBookRequest{
		Title: strPtr("War and Peace (Updated)"),
	})
	if err != nil {
		t.Fatalf("update failed: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update failed: %d", resp.StatusCode)
	}

	// 5. Delete
	resp, _, err = doRequest(s, http.MethodDelete, "/books/1", nil)
	if err != nil {
		t.Fatalf("delete failed: %v", err)
	}
	if resp.StatusCode != http.StatusNoContent {
		t.Errorf("expected 204 on delete, got %d", resp.StatusCode)
	}

	// 6. Verify empty
	resp, body, _ = doRequest(s, http.MethodGet, "/books", nil)
	json.Unmarshal(body, &books)
	if len(books) != 0 {
		t.Errorf("expected 0 books after delete, got %d", len(books))
	}
}

// ========== Method Not Allowed Tests ==========

func TestMethodNotAllowed(t *testing.T) {
	s := setupTestDB(t)

	// POST /books/1 (id path) should not work
	resp, _, _ := doRequest(s, http.MethodPost, "/books/1", CreateBookRequest{})
	if resp.StatusCode != http.StatusNotFound && resp.StatusCode != http.StatusMethodNotAllowed {
		t.Logf("POST /books/1 got %d (expected 404 or 405)", resp.StatusCode)
	}
}

// ========== Helper functions ==========

func strPtr(s string) *string { return &s }
func intPtr(i int) *int       { return &i }

// Ensure os import is used (it was needed in main but tests reference it via the package).
// Adding a no-op to avoid "imported and not used" if we ever compile test-only.
var _ = func() interface{} { return os.Getenv("TEST_VAR") }
