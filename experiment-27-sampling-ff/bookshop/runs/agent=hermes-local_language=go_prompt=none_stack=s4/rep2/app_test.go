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

func setupTestDB() (*sql.DB, error) {
	os.Remove("./books_test.db")

	var err error
	db, err = sql.Open("sqlite3", "./books_test.db")
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

func setBookIDParam(c *gin.Context, id string) {
	c.Params = gin.Params{
		{Key: "id", Value: id},
	}
}

func TestHealthCheck(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/health", nil)

	healthCheck(c)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Errorf("Expected status 'ok', got %v", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	})
	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewBuffer(body))

	createBook(c)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got %s", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got %s", book.Author)
	}
	if book.Year != 1925 {
		t.Errorf("Expected year 1925, got %d", book.Year)
	}
	if book.ID == 0 {
		t.Error("Expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	body, _ := json.Marshal(CreateBookRequest{
		Author: "Test Author",
	})
	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewBuffer(body))

	createBook(c)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing title, got %d", w.Code)
	}

	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)
	body, _ = json.Marshal(CreateBookRequest{
		Title: "Test Book",
	})
	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewBuffer(body))

	createBook(c)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing author, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"To Kill a Mockingbird", "Harper Lee", 1960, "978-0061120084")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books", nil)

	listBooks(c)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 2 {
		t.Errorf("Expected 2 books, got %d", len(books))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"To Kill a Mockingbird", "Harper Lee", 1960, "978-0061120084")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books?author=F.+Scott+Fitzgerald", nil)

	listBooks(c)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 1 {
		t.Errorf("Expected 1 book for author filter, got %d", len(books))
	}
	if books[0].Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got %s", books[0].Author)
	}
}

func TestGetBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books/1", nil)
	setBookIDParam(c, "1")

	getBook(c)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", w.Code, w.Body.String())
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got %s", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books/999", nil)
	setBookIDParam(c, "999")

	getBook(c)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	body, _ := json.Marshal(UpdateBookRequest{
		Title: "The Great Gatsby (Updated)",
	})
	c.Request, _ = http.NewRequest("PUT", "/books/1", bytes.NewBuffer(body))
	setBookIDParam(c, "1")

	updateBook(c)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", w.Code, w.Body.String())
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "The Great Gatsby (Updated)" {
		t.Errorf("Expected updated title, got %s", book.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("DELETE", "/books/1", nil)
	setBookIDParam(c, "1")

	deleteBook(c)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var count int
	err = db.QueryRow("SELECT COUNT(*) FROM books").Scan(&count)
	if err != nil {
		t.Fatalf("Failed to query count: %v", err)
	}
	if count != 0 {
		t.Errorf("Expected 0 books after deletion, got %d", count)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("DELETE", "/books/999", nil)
	setBookIDParam(c, "999")

	deleteBook(c)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	body, _ := json.Marshal(UpdateBookRequest{
		Title: "Updated Title",
	})
	c.Request, _ = http.NewRequest("PUT", "/books/999", bytes.NewBuffer(body))
	setBookIDParam(c, "999")

	updateBook(c)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestGetBookInvalidID(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books/abc", nil)
	setBookIDParam(c, "abc")

	getBook(c)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestEmptyListBooks(t *testing.T) {
	_, err := setupTestDB()
	if err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books", nil)

	listBooks(c)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 0 {
		t.Errorf("Expected empty list, got %d books", len(books))
	}
}
