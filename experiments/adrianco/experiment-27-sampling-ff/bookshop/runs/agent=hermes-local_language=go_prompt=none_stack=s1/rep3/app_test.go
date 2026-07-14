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

var router *gin.Engine

func setupRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.Default()

	r.GET("/health", healthHandler)

	books := r.Group("/books")
	{
		books.POST("", createBookHandler)
		books.GET("", listBooksHandler)
		books.GET("/:id", getBookHandler)
		books.PUT("/:id", updateBookHandler)
		books.DELETE("/:id", deleteBookHandler)
	}

	return r
}

// resetDB drops and recreates the books table, clearing all data
func resetDB() {
	db.Exec("DROP TABLE IF EXISTS books")
	db.Exec(`
		CREATE TABLE books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER,
			isbn TEXT
		);
	`)
}

func TestMain(m *testing.M) {
	router = setupRouter()
	var err error
	db, err = sql.Open("sqlite3", ":memory:")
	if err != nil {
		panic(err)
	}
	resetDB()
	code := m.Run()
	db.Close()
	os.Exit(code)
}

func TestHealthEndpoint(t *testing.T) {
	resetDB()
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

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
	resetDB()
	w := httptest.NewRecorder()
	body := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0743273565",
	}
	jsonBody, _ := json.Marshal(body)

	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got %s", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got %s", book.Author)
	}
	if book.Year != 1925 {
		t.Errorf("expected year 1925, got %d", book.Year)
	}
	if book.ISBN != "978-0743273565" {
		t.Errorf("expected isbn '978-0743273565', got %s", book.ISBN)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	resetDB()
	w := httptest.NewRecorder()
	body := map[string]interface{}{
		"title": "No Author Book",
	}
	jsonBody, _ := json.Marshal(body)

	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	resetDB()
	// Create test data
	w := httptest.NewRecorder()
	body := map[string]interface{}{
		"title":  "1984",
		"author": "George Orwell",
		"year":   1949,
		"isbn":   "978-0451524935",
	}
	jsonBody, _ := json.Marshal(body)

	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	// Create another book
	w = httptest.NewRecorder()
	body = map[string]interface{}{
		"title":  "Animal Farm",
		"author": "George Orwell",
		"year":   1945,
		"isbn":   "978-0451526342",
	}
	jsonBody, _ = json.Marshal(body)

	req, _ = http.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	// List all books
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 2 {
		t.Errorf("expected 2 books, got %d", len(books))
	}

	// Filter by author
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books?author=George%20Orwell", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var filteredBooks []Book
	json.Unmarshal(w.Body.Bytes(), &filteredBooks)

	if len(filteredBooks) != 2 {
		t.Errorf("expected 2 filtered books, got %d", len(filteredBooks))
	}
}

func TestGetBook(t *testing.T) {
	resetDB()
	// Create a book first
	w := httptest.NewRecorder()
	body := map[string]interface{}{
		"title":  "To Kill a Mockingbird",
		"author": "Harper Lee",
		"year":   1960,
		"isbn":   "978-0061120084",
	}
	jsonBody, _ := json.Marshal(body)

	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	var createdBook Book
	json.Unmarshal(w.Body.Bytes(), &createdBook)

	// Get the book by ID
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "To Kill a Mockingbird" {
		t.Errorf("expected title 'To Kill a Mockingbird', got %s", book.Title)
	}
	if book.ID != int(createdBook.ID) {
		t.Errorf("expected ID %d, got %d", createdBook.ID, book.ID)
	}
}

func TestGetBookNotFound(t *testing.T) {
	resetDB()
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/999", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	resetDB()
	// Create a book first
	w := httptest.NewRecorder()
	body := map[string]interface{}{
		"title":  "Original Title",
		"author": "Original Author",
		"year":   2000,
		"isbn":   "123-456",
	}
	jsonBody, _ := json.Marshal(body)

	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	// Update the book
	w = httptest.NewRecorder()
	body = map[string]interface{}{
		"title": "Updated Title",
	}
	jsonBody, _ = json.Marshal(body)

	req, _ = http.NewRequest("PUT", "/books/1", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "Updated Title" {
		t.Errorf("expected title 'Updated Title', got %s", book.Title)
	}
	if book.Author != "Original Author" {
		t.Errorf("expected author to remain 'Original Author', got %s", book.Author)
	}
}

func TestDeleteBook(t *testing.T) {
	resetDB()
	// Create a book first
	w := httptest.NewRecorder()
	body := map[string]interface{}{
		"title":  "Book to Delete",
		"author": "Delete Author",
		"year":   2020,
		"isbn":   "delete-isbn",
	}
	jsonBody, _ := json.Marshal(body)

	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	// Delete the book
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	// Verify it's deleted
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404 after delete, got %d", w.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	resetDB()
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/999", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestListBooksEmpty(t *testing.T) {
	resetDB()
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("expected 0 books, got %d", len(books))
	}
}
