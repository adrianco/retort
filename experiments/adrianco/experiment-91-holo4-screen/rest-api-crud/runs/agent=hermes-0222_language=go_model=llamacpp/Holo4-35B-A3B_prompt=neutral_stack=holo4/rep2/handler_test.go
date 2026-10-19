package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"
)

func setupTestDB(t *testing.T) *sql.DB {
	t.Helper()
	// Use a temporary in-memory-like file for testing
	tmpFile, err := os.CreateTemp("", "test_books_*.db")
	if err != nil {
		t.Fatalf("failed to create temp db: %v", err)
	}
	tmpFile.Close()

	testDB, err := sql.Open("sqlite", tmpFile.Name()+"?cache=shared&_journal_mode=WAL")
	if err != nil {
		t.Fatalf("failed to open test db: %v", err)
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT UNIQUE NOT NULL
	);`
	if _, err := testDB.Exec(createTable); err != nil {
		t.Fatalf("failed to create test table: %v", err)
	}

	// Save the original db and replace with test db
	origDB := db
	db = testDB
	t.Cleanup(func() {
		db = origDB
		testDB.Close()
		os.Remove(tmpFile.Name())
	})

	return testDB
}

func TestHealthEndpoint(t *testing.T) {
	setupTestDB(t)

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
	setupTestDB(t)

	body := bytes.NewBufferString(`{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}`)
	req := httptest.NewRequest(http.MethodPost, "/books", body)
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
	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got %s", book.Title)
	}
	if book.ID != 1 {
		t.Errorf("expected id 1, got %d", book.ID)
	}
}

func TestCreateBookValidation(t *testing.T) {
	setupTestDB(t)

	// Missing title
	body := bytes.NewBufferString(`{"author":"Some Author","year":2020,"isbn":"123"}`)
	req := httptest.NewRequest(http.MethodPost, "/books", body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	booksHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	setupTestDB(t)

	// Create two books
	createBookJSON(t, "The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	createBookJSON(t, "Tender Is the Night", "F. Scott Fitzgerald", 1934, "978-0684801544")
	createBookJSON(t, "1984", "George Orwell", 1949, "978-0451524935")

	// List all
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	booksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}

	// Filter by author
	u := "/books"
	q := u + "?author=" + url.QueryEscape("F. Scott Fitzgerald")
	req = httptest.NewRequest(http.MethodGet, q, nil)
	w = httptest.NewRecorder()
	booksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", w.Code)
	}

	var filtered []Book
	if err := json.NewDecoder(w.Body).Decode(&filtered); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("expected 2 books for author filter, got %d", len(filtered))
	}
}

func TestGetBook(t *testing.T) {
	setupTestDB(t)
	createBookJSON(t, "1984", "George Orwell", 1949, "978-0451524935")

	req := httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w := httptest.NewRecorder()
	booksByIDHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if book.Title != "1984" || book.Author != "George Orwell" {
		t.Errorf("unexpected book: %+v", book)
	}
}

func TestGetBookNotFound(t *testing.T) {
	setupTestDB(t)

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()
	booksByIDHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	setupTestDB(t)
	createBookJSON(t, "1984", "George Orwell", 1949, "978-0451524935")

	body := bytes.NewBufferString(`{"year":1950}`)
	req := httptest.NewRequest(http.MethodPut, "/books/1", body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	booksByIDHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if book.Year != 1950 {
		t.Errorf("expected year 1950, got %d", book.Year)
	}
}

func TestDeleteBook(t *testing.T) {
	setupTestDB(t)
	createBookJSON(t, "1984", "George Orwell", 1949, "978-0451524935")

	req := httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	w := httptest.NewRecorder()
	booksByIDHandler(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("expected status 204, got %d", w.Code)
	}

	// Verify it's gone
	req = httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w = httptest.NewRecorder()
	booksByIDHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404 after delete, got %d", w.Code)
	}
}

func createBookJSON(t *testing.T, title, author string, year int, isbn string) {
	t.Helper()
	data, err := json.Marshal(CreateBookRequest{Title: title, Author: author, Year: year, ISBN: isbn})
	if err != nil {
		t.Fatalf("failed to marshal test book: %v", err)
	}
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(data))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	booksHandler(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("failed to create test book: status %d, body: %s", w.Code, w.Body.String())
	}
}
