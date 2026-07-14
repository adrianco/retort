package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func setupTestDB() (*sql.DB, error) {
	os.Remove("./books_test.db")

	var err error
	db, err = sql.Open("sqlite3", "./books_test.db")
	if err != nil {
		return nil, err
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = db.Exec(createTable)
	if err != nil {
		return nil, err
	}

	return db, nil
}

func teardownTestDB() {
	if db != nil {
		db.Close()
	}
	os.Remove("./books_test.db")
}

func TestMain(m *testing.M) {
	db = nil
	os.Remove("./books_test.db")

	code := m.Run()

	teardownTestDB()
	os.Exit(code)
}

func newTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.Default()

	r.GET("/health", healthCheck)
	r.POST("/books", createBook)
	r.GET("/books", listBooks)
	r.GET("/books/:id", getBook)
	r.PUT("/books/:id", updateBook)
	r.DELETE("/books/:id", deleteBook)

	return r
}

func TestHealthCheck(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got %v", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	tests := []struct {
		name       string
		body       string
		wantStatus int
	}{
		{
			name:       "valid book",
			body:       `{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}`,
			wantStatus: http.StatusCreated,
		},
		{
			name:       "missing title",
			body:       `{"author":"Some Author"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "missing author",
			body:       `{"title":"Some Title"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "empty title",
			body:       `{"title":"","author":"Some Author"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "empty author",
			body:       `{"title":"Some Title","author":""}`,
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(tt.body))
			req.Header.Set("Content-Type", "application/json")
			newTestRouter().ServeHTTP(w, req)

			if w.Code != tt.wantStatus {
				t.Errorf("expected status %d, got %d; body: %s", tt.wantStatus, w.Code, w.Body.String())
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	// Insert test data
	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book A", "Author X", 2020, "isbn-1")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book B", "Author Y", 2021, "isbn-2")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book C", "Author X", 2022, "isbn-3")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	// Test list all
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}

	// Test filter by author
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books?author=Author+X", nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var filtered []Book
	json.Unmarshal(w.Body.Bytes(), &filtered)
	if len(filtered) != 2 {
		t.Errorf("expected 2 books for Author X, got %d", len(filtered))
	}
}

func TestGetBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	// Insert a test book
	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "isbn-test")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	id, _ := result.LastInsertId()

	// Test get existing book
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", fmt.Sprintf("/books/%d", id), nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "Test Book" {
		t.Errorf("expected title 'Test Book', got '%s'", book.Title)
	}

	// Test get non-existent book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/9999", nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}

	// Test invalid ID
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/abc", nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	// Insert a test book
	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Old Title", "Old Author", 2020, "old-isbn")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	id, _ := result.LastInsertId()

	// Test update
	body := `{"title":"New Title","year":2024}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", fmt.Sprintf("/books/%d", id), bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d; body: %s", w.Code, w.Body.String())
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["title"] != "New Title" {
		t.Errorf("expected title 'New Title', got %v", resp["title"])
	}
	if resp["author"] != "Old Author" {
		t.Errorf("expected author to remain 'Old Author', got %v", resp["author"])
	}
	if resp["year"] != float64(2024) {
		t.Errorf("expected year 2024, got %v", resp["year"])
	}

	// Test update non-existent book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("PUT", "/books/9999", bytes.NewBufferString(`{"title":"X"}`))
	req.Header.Set("Content-Type", "application/json")
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	// Insert a test book
	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author", 2023, "isbn-del")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	id, _ := result.LastInsertId()

	// Test delete existing
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("/books/%d", id), nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	// Verify it's gone
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", fmt.Sprintf("/books/%d", id), nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404 after delete, got %d", w.Code)
	}

	// Test delete non-existent
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/9999", nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404 for non-existent, got %d", w.Code)
	}
}

func TestEmptyList(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 0 {
		t.Errorf("expected empty list, got %d books", len(books))
	}
}
