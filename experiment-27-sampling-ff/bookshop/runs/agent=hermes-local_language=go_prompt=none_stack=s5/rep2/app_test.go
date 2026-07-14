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

func setupTestDB() (*gin.Engine, *sql.DB, error) {
	tmpFile := "test_books.db"

	var err error
	db, err = sql.Open("sqlite3", tmpFile)
	if err != nil {
		return nil, nil, err
	}

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	if _, err := db.Exec(createTableSQL); err != nil {
		return nil, nil, err
	}

	r := gin.Default()
	r.GET("/health", healthCheck)

	books := r.Group("/books")
	{
		books.POST("", createBook)
		books.GET("", listBooks)
		books.GET("/:id", getBook)
		books.PUT("/:id", updateBook)
		books.DELETE("/:id", deleteBook)
	}

	return r, db, nil
}

func cleanupTestDB(db *sql.DB) {
	db.Close()
	os.Remove("test_books.db")
}

func TestHealthCheck(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	if resp["status"] != "ok" {
		t.Errorf("Expected status 'ok', got '%s'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	body := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0743273565",
	}

	w := httptest.NewRecorder()
	reqBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", "/books", bytes.NewReader(reqBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got '%s'", book.Title)
	}

	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}

	if book.Year != 1925 {
		t.Errorf("Expected year 1925, got %d", book.Year)
	}

	if book.ID == 0 {
		t.Error("Expected non-zero ID")
	}

	if book.ISBN != "978-0743273565" {
		t.Errorf("Expected ISBN '978-0743273565', got '%s'", book.ISBN)
	}
}

func TestCreateBookMissingTitle(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	body := map[string]interface{}{
		"author": "F. Scott Fitzgerald",
	}

	w := httptest.NewRecorder()
	reqBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", "/books", bytes.NewReader(reqBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	if _, ok := resp["error"]; !ok {
		t.Error("Expected error message in response")
	}
}

func TestListBooks(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"To Kill a Mockingbird", "Harper Lee", 1960, "978-0446310789")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"1984", "George Orwell", 1949, "978-0451524935")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books?author=F. Scott Fitzgerald", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 1 {
		t.Errorf("Expected 1 book for author filter, got %d", len(books))
	}

	if books[0].Title != "The Great Gatsby" {
		t.Errorf("Expected 'The Great Gatsby', got '%s'", books[0].Title)
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books?author=NonExistentAuthor", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("Expected 0 books for non-existent author, got %d", len(books))
	}
}

func TestGetBook(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got '%s'", book.Title)
	}

	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/abc", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")

	body := map[string]interface{}{
		"title": "The Great Gatsby (Updated)",
	}

	w := httptest.NewRecorder()
	reqBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("PUT", "/books/1", bytes.NewReader(reqBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Great Gatsby (Updated)" {
		t.Errorf("Expected updated title, got '%s'", book.Title)
	}

	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected unchanged author, got '%s'", book.Author)
	}

	if book.Year != 1925 {
		t.Errorf("Expected unchanged year, got %d", book.Year)
	}

	w = httptest.NewRecorder()
	reqBody, _ = json.Marshal(body)
	req, _ = http.NewRequest("PUT", "/books/999", bytes.NewReader(reqBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 for non-existent book, got %d", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	if _, ok := resp["message"]; !ok {
		t.Error("Expected success message in response")
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 after deletion, got %d", w.Code)
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 for non-existent book, got %d", w.Code)
	}

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/books/abc", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for invalid ID, got %d", w.Code)
	}
}

func TestCreateBookMissingAuthor(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	body := map[string]interface{}{
		"title": "The Great Gatsby",
	}

	w := httptest.NewRecorder()
	reqBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", "/books", bytes.NewReader(reqBody))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	if _, ok := resp["error"]; !ok {
		t.Error("Expected error message in response")
	}
}

func TestCreateBookEmptyBody(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	if _, ok := resp["error"]; !ok {
		t.Error("Expected error message in response")
	}
}

func TestListBooksEmpty(t *testing.T) {
	r, db, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test: %v", err)
	}
	defer cleanupTestDB(db)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("Expected empty list, got %d books", len(books))
	}

	if books == nil {
		t.Error("Expected empty array, got null")
	}
}
