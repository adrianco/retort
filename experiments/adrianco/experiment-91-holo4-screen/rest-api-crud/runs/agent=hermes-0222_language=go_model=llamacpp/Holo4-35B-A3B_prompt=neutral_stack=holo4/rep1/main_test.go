package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func setupTestDB(t *testing.T) {
	var err error
	db, err = sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open test DB: %v", err)
	}
	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`
	_, err = db.Exec(createTable)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}
}

func TestHealthEndpoint(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

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
	if resp["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if book.Title != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%s'", book.Title)
	}
	if book.Author != "Alan Donovan" {
		t.Errorf("Expected author 'Alan Donovan', got '%s'", book.Author)
	}
	if book.Year != 2015 {
		t.Errorf("Expected year 2015, got %d", book.Year)
	}
	if book.ISBN != "978-0134190440" {
		t.Errorf("Expected ISBN '978-0134190440', got '%s'", book.ISBN)
	}
	if book.ID != 1 {
		t.Errorf("Expected ID 1, got %d", book.ID)
	}
}

func TestCreateBookValidation(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	tests := []struct {
		name     string
		request  CreateBookRequest
		wantCode int
		wantErr  string
	}{
		{
			name:     "missing title",
			request:  CreateBookRequest{Author: "Author", Year: 2020, ISBN: "123"},
			wantCode: http.StatusBadRequest,
			wantErr:  "Title is required",
		},
		{
			name:     "missing author",
			request:  CreateBookRequest{Title: "Title", Year: 2020, ISBN: "123"},
			wantCode: http.StatusBadRequest,
			wantErr:  "Author is required",
		},
		{
			name:     "missing year",
			request:  CreateBookRequest{Title: "Title", Author: "Author", ISBN: "123"},
			wantCode: http.StatusBadRequest,
			wantErr:  "Year is required",
		},
		{
			name:     "missing isbn",
			request:  CreateBookRequest{Title: "Title", Author: "Author", Year: 2020},
			wantCode: http.StatusBadRequest,
			wantErr:  "ISBN is required",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body, _ := json.Marshal(tt.request)
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()

			createBookHandler(w, req)

			if w.Code != tt.wantCode {
				t.Errorf("Expected status %d, got %d", tt.wantCode, w.Code)
			}

			var resp map[string]string
			json.NewDecoder(w.Body).Decode(&resp)
			if resp["error"] != tt.wantErr {
				t.Errorf("Expected error '%s', got '%s'", tt.wantErr, resp["error"])
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	// Insert test data
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "ISBN-001")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "ISBN-002")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Three", "Author A", 2022, "ISBN-003")

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()

	listBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}
}

func TestListBooksAuthorFilter(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "ISBN-001")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "ISBN-002")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Three", "Author A", 2022, "ISBN-003")

	req := httptest.NewRequest(http.MethodGet, "/books?author=Author%20A", nil)
	w := httptest.NewRecorder()

	listBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) != 2 {
		t.Errorf("Expected 2 books for Author A, got %d", len(books))
	}
}

func TestGetBook(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "ISBN-TEST")

	req := httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w := httptest.NewRecorder()

	getBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if book.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()

	getBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Original Title", "Original Author", 2020, "ISBN-001")

	body, _ := json.Marshal(UpdateBookRequest{
		Title:  ptrString("Updated Title"),
		Author: ptrString("Updated Author"),
	})

	req := httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	updateBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if book.Title != "Updated Title" {
		t.Errorf("Expected title 'Updated Title', got '%s'", book.Title)
	}
	if book.Author != "Updated Author" {
		t.Errorf("Expected author 'Updated Author', got '%s'", book.Author)
	}
}

func TestDeleteBook(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author", 2020, "ISBN-DEL")

	req := httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	w := httptest.NewRecorder()

	deleteBookHandler(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status 204, got %d", w.Code)
	}

	// Verify it's gone
	req2 := httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w2 := httptest.NewRecorder()
	getBookHandler(w2, req2)

	if w2.Code != http.StatusNotFound {
		t.Errorf("Expected 404 after delete, got %d", w2.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
	w := httptest.NewRecorder()

	deleteBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func ptrString(s string) *string { return &s }
