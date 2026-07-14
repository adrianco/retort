package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

const testDBPath = "test_books.db"

func setupTestDB() (*Database, error) {
	db, err := NewDatabase(testDBPath)
	if err != nil {
		return nil, err
	}
	return db, nil
}

func teardownTestDB() {
	os.Remove(testDBPath)
}

func setupTestRouter(db *Database) *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(gin.Recovery())

	router.GET("/health", HealthCheck)
	router.POST("/books", db.CreateBook)
	router.GET("/books", db.ListBooks)
	router.GET("/books/:id", db.GetBook)
	router.PUT("/books/:id", db.UpdateBook)
	router.DELETE("/books/:id", db.DeleteBook)

	return router
}

func TestCreateBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	payload := CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != payload.Title {
		t.Errorf("Expected title %s, got %s", payload.Title, book.Title)
	}
	if book.Author != payload.Author {
		t.Errorf("Expected author %s, got %s", payload.Author, book.Author)
	}
	if book.Year != payload.Year {
		t.Errorf("Expected year %d, got %d", payload.Year, book.Year)
	}
	if book.ISBN != payload.ISBN {
		t.Errorf("Expected ISBN %s, got %s", payload.ISBN, book.ISBN)
	}
	if book.ID == 0 {
		t.Error("Expected book ID to be set")
	}
}

func TestCreateBookMissingTitle(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	payload := CreateBookRequest{
		Title:  "",
		Author: "Test Author",
		Year:   2020,
		ISBN:   "123",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestCreateBookMissingAuthor(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	payload := CreateBookRequest{
		Title:  "Test Book",
		Author: "",
		Year:   2020,
		ISBN:   "123",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestListBooks(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	// Insert test data
	_, err = db.conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book A", "Author X", 2020, "isbn-a")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	_, err = db.conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book B", "Author Y", 2021, "isbn-b")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 2 {
		t.Errorf("Expected 2 books, got %d", len(books))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	// Insert test data
	_, err = db.conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book A", "Author X", 2020, "isbn-a")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	_, err = db.conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book B", "Author Y", 2021, "isbn-b")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books?author=Author%20X", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 1 {
		t.Errorf("Expected 1 book for author 'Author X', got %d", len(books))
	}
	if books[0].Author != "Author X" {
		t.Errorf("Expected author 'Author X', got '%s'", books[0].Author)
	}
}

func TestGetBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	// Insert test data
	result, err := db.conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "test-isbn")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	id, _ := result.LastInsertId()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/"+string(rune(id+'0')), nil)
	router.ServeHTTP(w, req)

	// Try with the actual ID
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/9999", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	// Insert test data
	_, err = db.conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Old Title", "Old Author", 2020, "old-isbn")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	payload := CreateBookRequest{
		Title:  "New Title",
		Author: "New Author",
		Year:   2024,
		ISBN:   "new-isbn",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/1", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "New Title" {
		t.Errorf("Expected title 'New Title', got '%s'", book.Title)
	}
	if book.Author != "New Author" {
		t.Errorf("Expected author 'New Author', got '%s'", book.Author)
	}
	if book.Year != 2024 {
		t.Errorf("Expected year 2024, got %d", book.Year)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	payload := CreateBookRequest{
		Title:  "New Title",
		Author: "New Author",
		Year:   2024,
		ISBN:   "new-isbn",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/9999", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	// Insert test data
	_, err = db.conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author", 2020, "delete-isbn")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	// Verify it's gone
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d after delete, got %d", http.StatusNotFound, w.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/9999", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestHealthCheck(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)

	if response["status"] != "ok" {
		t.Errorf("Expected status 'ok', got '%v'", response["status"])
	}
}

func TestListBooksEmpty(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("Expected 0 books, got %d", len(books))
	}
	if books == nil {
		t.Error("Expected empty array, got nil")
	}
}

func TestGetBookInvalidID(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/abc", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestCreateBookInvalidJSON(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer([]byte("not json")))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestIntegrationFullCRUD(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	router := setupTestRouter(db)

	// CREATE
	payload := CreateBookRequest{
		Title:  "Integration Test Book",
		Author: "Integration Author",
		Year:   2024,
		ISBN:   "int-isbn-123",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("CREATE failed: expected status %d, got %d", http.StatusCreated, w.Code)
	}

	// READ
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("READ failed: expected status %d, got %d", http.StatusOK, w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != payload.Title {
		t.Errorf("READ title mismatch: expected '%s', got '%s'", payload.Title, book.Title)
	}

	// UPDATE
	updatePayload := CreateBookRequest{
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2025,
		ISBN:   "updated-isbn",
	}
	updateBody, _ := json.Marshal(updatePayload)

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("PUT", "/books/1", bytes.NewBuffer(updateBody))
	req.Header.Set("Content-Type", "http://json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("UPDATE failed: expected status %d, got %d", http.StatusOK, w.Code)
	}

	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "Updated Title" {
		t.Errorf("UPDATE title mismatch: expected 'Updated Title', got '%s'", book.Title)
	}

	// DELETE
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("DELETE failed: expected status %d, got %d", http.StatusOK, w.Code)
	}

	// Verify deleted
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("After DELETE, expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestMain(m *testing.M) {
	// Clean up test DB before running tests
	os.Remove(testDBPath)
	code := m.Run()
	// Clean up after
	os.Remove(testDBPath)
	os.Exit(code)
}
