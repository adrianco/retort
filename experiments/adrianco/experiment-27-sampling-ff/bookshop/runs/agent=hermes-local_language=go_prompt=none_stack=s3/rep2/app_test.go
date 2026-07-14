package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// setupTestDB creates an in-memory SQLite database for testing.
func setupTestDB(t *testing.T) {
	var err error
	db, err = sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open test database: %v", err)
	}

	createTable := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	if _, err := db.Exec(createTable); err != nil {
		t.Fatalf("Failed to create test table: %v", err)
	}
}

// teardownTestDB closes the database.
func teardownTestDB(t *testing.T) {
	if db != nil {
		db.Close()
	}
}

// newTestRouter returns a Gin router with all routes attached.
func newTestRouter() *gin.Engine {
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

// TestHealthCheck verifies the health endpoint returns 200 OK.
func TestHealthCheck(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200; got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok'; got %v", resp["status"])
	}
}

// TestCreateBook verifies POST /books creates a book and returns 201.
func TestCreateBook(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	payload, _ := json.Marshal(CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201; got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language'; got %s", book.Title)
	}
	if book.Author != "Alan Donovan" {
		t.Errorf("expected author 'Alan Donovan'; got %s", book.Author)
	}
	if book.Year != 2015 {
		t.Errorf("expected year 2015; got %d", book.Year)
	}
	if book.ISBN != "978-0134190440" {
		t.Errorf("expected isbn '978-0134190440'; got %s", book.ISBN)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

// TestCreateBookValidation verifies that missing title/author returns 400.
func TestCreateBookValidation(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	// Missing title and author.
	payload, _ := json.Marshal(CreateBookRequest{Year: 2020})

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400; got %d", w.Code)
	}
}

// TestListBooks verifies GET /books returns all books.
func TestListBooks(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	// Insert two books.
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book A", "Author X", 2020, "isbn-a")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book B", "Author Y", 2021, "isbn-b")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200; got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 2 {
		t.Errorf("expected 2 books; got %d", len(books))
	}
}

// TestListBooksByAuthor verifies GET /books?author= filters correctly.
func TestListBooksByAuthor(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book A", "Author X", 2020, "isbn-a")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book B", "Author X", 2021, "isbn-b")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book C", "Author Y", 2022, "isbn-c")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books?author=Author+X", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200; got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 2 {
		t.Errorf("expected 2 books for Author X; got %d", len(books))
	}
}

// TestGetBook verifies GET /books/:id returns a single book.
func TestGetBook(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	res, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "isbn-test")
	id, _ := res.LastInsertId()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", fmt.Sprintf("/books/%d", id), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200; got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "Test Book" {
		t.Errorf("expected title 'Test Book'; got %s", book.Title)
	}
}

// TestGetBookNotFound verifies GET /books/:id returns 404 for missing book.
func TestGetBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/9999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404; got %d", w.Code)
	}
}

// TestUpdateBook verifies PUT /books/:id updates a book.
func TestUpdateBook(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	res, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Old Title", "Old Author", 2020, "old-isbn")
	id, _ := res.LastInsertId()

	payload, _ := json.Marshal(UpdateBookRequest{Title: "New Title", Year: 2024})

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", fmt.Sprintf("/books/%d", id), bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200; got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "New Title" {
		t.Errorf("expected title 'New Title'; got %s", book.Title)
	}
	if book.Year != 2024 {
		t.Errorf("expected year 2024; got %d", book.Year)
	}
	if book.Author != "Old Author" {
		t.Errorf("expected author unchanged; got %s", book.Author)
	}
}

// TestDeleteBook verifies DELETE /books/:id removes a book.
func TestDeleteBook(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	res, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author", 2023, "isbn-del")
	id, _ := res.LastInsertId()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("/books/%d", id), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200; got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["message"] != "book deleted" {
		t.Errorf("expected message 'book deleted'; got %v", resp["message"])
	}

	// Verify it's actually gone.
	var count int
	db.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&count)
	if count != 0 {
		t.Error("expected book to be deleted")
	}
}

// TestDeleteBookNotFound verifies DELETE /books/:id returns 404 for missing book.
func TestDeleteBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/9999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404; got %d", w.Code)
	}
}

// TestUpdateBookNotFound verifies PUT /books/:id returns 404 for missing book.
func TestUpdateBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	payload, _ := json.Marshal(UpdateBookRequest{Title: "New Title"})

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/9999", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404; got %d", w.Code)
	}
}

// TestListBooksEmpty verifies GET /books returns empty array when no books exist.
func TestListBooksEmpty(t *testing.T) {
	setupTestDB(t)
	defer teardownTestDB(t)

	r := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200; got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("expected 0 books; got %d", len(books))
	}
}
