package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

var testDB *sql.DB

func setupTestDB() error {
	os.Remove("./test_books.db")

	var err error
	testDB, err = sql.Open("sqlite3", "./test_books.db")
	if err != nil {
		return err
	}

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = testDB.Exec(createTableSQL)
	if err != nil {
		return err
	}

	return nil
}

func teardownTestDB() {
	testDB.Close()
	os.Remove("./test_books.db")
}

func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.Default()

	r.GET("/health", healthHandler)
	r.POST("/books", createBookHandler)
	r.GET("/books", listBooksHandler)
	r.GET("/books/:id", getBookHandler)
	r.PUT("/books/:id", updateBookHandler)
	r.DELETE("/books/:id", deleteBookHandler)

	return r
}

func insertBook(title, author string, year int, isbn string) error {
	_, err := testDB.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		title, author, year, isbn,
	)
	return err
}

func TestHealthEndpoint(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Errorf("Expected status 'ok', got '%v'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	// Inject test DB into the global db variable used by handlers
	db = testDB

	r := setupTestRouter()

	payload := `{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["title"] != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%v'", resp["title"])
	}
	if resp["author"] != "Alan Donovan" {
		t.Errorf("Expected author 'Alan Donovan', got '%v'", resp["author"])
	}
}

func TestCreateBookMissingTitle(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	payload := `{"author":"Test Author"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestCreateBookMissingAuthor(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	payload := `{"title":"Test Book"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	db = testDB

	insertBook("Book A", "Author X", 2020, "isbn-a")
	insertBook("Book B", "Author X", 2021, "isbn-b")
	insertBook("Book C", "Author Y", 2022, "isbn-c")

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books?author=Author+X", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 2 {
		t.Errorf("Expected 2 books for Author X, got %d", len(books))
	}
}

func TestGetBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	db = testDB

	insertBook("Test Book", "Test Author", 2023, "isbn-123")

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["title"] != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%v'", resp["title"])
	}
}

func TestGetBookNotFound(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	db = testDB

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	db = testDB

	insertBook("Original Title", "Original Author", 2020, "isbn-old")

	r := setupTestRouter()

	payload := `{"title":"Updated Title","year":2024}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/1", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["title"] != "Updated Title" {
		t.Errorf("Expected title 'Updated Title', got '%v'", resp["title"])
	}
	if resp["author"] != "Original Author" {
		t.Errorf("Expected author 'Original Author', got '%v'", resp["author"])
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	db = testDB

	r := setupTestRouter()

	payload := `{"title":"New Title"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/999", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	db = testDB

	insertBook("To Delete", "Author", 2023, "isbn-del")

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 after delete, got %d", w.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	db = testDB

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestGetBookInvalidID(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/abc", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestCreateBookEmptyBody(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString("{}"))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}
