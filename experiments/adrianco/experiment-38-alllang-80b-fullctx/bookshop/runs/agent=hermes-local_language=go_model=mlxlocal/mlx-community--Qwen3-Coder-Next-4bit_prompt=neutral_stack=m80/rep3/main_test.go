package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func setupTestDB() (*sql.DB, error) {
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		return nil, err
	}

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func setupAPIHandler(db *sql.DB) *APIHandler {
	return NewAPIHandler(db)
}

func setupRouter(handler *APIHandler) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", handler.healthHandler)
	mux.HandleFunc("/books", handler.booksHandler)
	mux.HandleFunc("/books/", handler.bookHandler)
	return mux
}

func TestHealthEndpoint(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, rec.Code)
	}

	var resp HealthResponse
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if resp.Status != "ok" {
		t.Errorf("Expected status 'ok', got '%s'", resp.Status)
	}
}

func TestCreateBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	book := Book{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, rec.Code)
	}

	var resp Book
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if resp.Title != book.Title {
		t.Errorf("Expected title '%s', got '%s'", book.Title, resp.Title)
	}
	if resp.Author != book.Author {
		t.Errorf("Expected author '%s', got '%s'", book.Author, resp.Author)
	}
	if resp.ID == 0 {
		t.Error("Expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	book := Book{
		Title:  "",  // Invalid: empty title
		Author: "Some Author",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d for validation error, got %d", http.StatusBadRequest, rec.Code)
	}
}

func TestGetAllBooks(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	// Create a book first
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	// Get all books
	req = httptest.NewRequest(http.MethodGet, "/books", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, rec.Code)
	}

	var books []Book
	if err := json.NewDecoder(rec.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}
}

func TestGetBookByID(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	// Create a book first
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	// Get the created book
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, rec.Code)
	}

	var resp Book
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if resp.Title != book.Title {
		t.Errorf("Expected title '%s', got '%s'", book.Title, resp.Title)
	}
}

func TestGetBookByIDNotFound(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, rec.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	// Create a book first
	book := Book{
		Title:  "Original Title",
		Author: "Original Author",
		Year:   2020,
		ISBN:   "1234567890",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	// Update the book
	updatedBook := Book{
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2023,
		ISBN:   "0987654321",
	}

	body, _ = json.Marshal(updatedBook)
	req = httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewBuffer(body))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, rec.Code)
	}

	var resp Book
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if resp.Title != updatedBook.Title {
		t.Errorf("Expected title '%s', got '%s'", updatedBook.Title, resp.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	// Create a book first
	book := Book{
		Title:  "To Delete",
		Author: "Delete Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	body, _ := json.Marshal(book)
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	// Delete the book
	req = httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d", http.StatusNoContent, rec.Code)
	}

	// Verify the book is gone
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("Expected status %d after deletion, got %d", http.StatusNotFound, rec.Code)
	}
}

func TestGetBooksByAuthor(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	// Create books with different authors
	books := []Book{
		{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "111"},
		{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "222"},
		{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "333"},
	}

	for _, b := range books {
		body, _ := json.Marshal(b)
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(body))
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
	}

	// Filter by author
	req := httptest.NewRequest(http.MethodGet, "/books?author=Author+A", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, rec.Code)
	}

	var booksResult []Book
	if err := json.NewDecoder(rec.Body).Decode(&booksResult); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(booksResult) != 2 {
		t.Errorf("Expected 2 books by Author A, got %d", len(booksResult))
	}

	for _, b := range booksResult {
		if b.Author != "Author A" {
			t.Errorf("Expected book author 'Author A', got '%s'", b.Author)
		}
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, rec.Code)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	updatedBook := Book{
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2023,
		ISBN:   "0987654321",
	}

	body, _ := json.Marshal(updatedBook)
	req := httptest.NewRequest(http.MethodPut, "/books/999", bytes.NewBuffer(body))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, rec.Code)
	}
}

func TestInvalidBookID(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer db.Close()

	handler := setupAPIHandler(db)
	mux := setupRouter(handler)

	req := httptest.NewRequest(http.MethodGet, "/books/invalid", nil)
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d for invalid ID, got %d", http.StatusBadRequest, rec.Code)
	}
}

func cleanupTestDB() {
	os.Remove("books.db")
}

func TestMain(m *testing.M) {
	// Setup
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize test DB: %v", err)
	}

	// Run tests
	code := m.Run()

	// Cleanup
	cleanupTestDB()

	os.Exit(code)
}
