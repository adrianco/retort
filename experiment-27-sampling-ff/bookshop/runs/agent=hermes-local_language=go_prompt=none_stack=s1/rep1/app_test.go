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

func setupTestDB() error {
	// Close existing db if open
	if db != nil {
		db.Close()
	}

	os.Remove("./test_books.db")

	var err error
	db, err = sql.Open("sqlite3", "./test_books.db")
	if err != nil {
		return err
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
		return err
	}

	return nil
}

func teardownTestDB() {
	if db != nil {
		db.Close()
		db = nil
	}
	os.Remove("./test_books.db")
}

func setupTestRouter() *gin.Engine {
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

	var response map[string]string
	json.Unmarshal(w.Body.Bytes(), &response)
	if response["status"] != "ok" {
		t.Errorf("Expected status 'ok', got '%s'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	book := Book{Title: "The Great Gatsby", Author: "F. Scott Fitzgerald", Year: 1925, ISBN: "978-0743273565"}
	body, _ := json.Marshal(book)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", w.Code)
	}

	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	if response.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got '%s'", response.Title)
	}
	if response.ID == 0 {
		t.Error("Expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	book := Book{Title: "", Author: "Test Author", Year: 2020, ISBN: "123"}
	body, _ := json.Marshal(book)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing title, got %d", w.Code)
	}

	book = Book{Title: "Test Book", Author: "", Year: 2020, ISBN: "123"}
	body, _ = json.Marshal(book)

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for missing author, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}
	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"1984", "George Orwell", 1949, "978-0451524935")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books?author=F.%20Scott%20Fitzgerald", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 1 {
		t.Errorf("Expected 1 book for author filter, got %d", len(books))
	}
	if books[0].Title != "The Great Gatsby" {
		t.Errorf("Expected 'The Great Gatsby', got '%s'", books[0].Title)
	}
}

func TestGetBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/1", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "The Great Gatsby" {
		t.Errorf("Expected 'The Great Gatsby', got '%s'", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

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

	_, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	r := setupTestRouter()

	updatedBook := Book{Title: "The Great Gatsby (Updated)", Author: "F. Scott Fitzgerald", Year: 1925, ISBN: "978-0743273565"}
	body, _ := json.Marshal(updatedBook)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/1", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response Book
	json.Unmarshal(w.Body.Bytes(), &response)
	if response.Title != "The Great Gatsby (Updated)" {
		t.Errorf("Expected updated title, got '%s'", response.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	_, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

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
		t.Errorf("Expected status 404 after deletion, got %d", w.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 for non-existent book, got %d", w.Code)
	}
}

func TestListBooksEmpty(t *testing.T) {
	if err := setupTestDB(); err != nil {
		t.Fatalf("Failed to setup test DB: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 0 {
		t.Errorf("Expected 0 books, got %d", len(books))
	}
}
