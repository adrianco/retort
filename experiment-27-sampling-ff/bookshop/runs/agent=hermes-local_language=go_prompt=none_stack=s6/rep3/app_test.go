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
	os.Remove("test_books.db")

	var err error
	db, err = sql.Open("sqlite3", "test_books.db")
	if err != nil {
		return err
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
	return err
}

func TestMain(m *testing.M) {
	gin.SetMode(gin.TestMode)
	os.Exit(m.Run())
}

// TestHealthEndpoint verifies the health check returns 200 OK
func TestHealthEndpoint(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/health", nil)
	healthHandler(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var body map[string]string
	json.NewDecoder(resp.Body).Decode(&body)
	if body["status"] != "ok" {
		t.Errorf("Expected status 'ok', got '%s'", body["status"])
	}
}

// TestCreateBook verifies creating a valid book returns 201
func TestCreateBook(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	r := gin.New()
	r.POST("/books", createBook)

	payload := bytes.NewBufferString(`{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}`)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("POST", "/books", payload)
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", resp.StatusCode)
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got '%s'", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}
	if book.ID != 1 {
		t.Errorf("Expected ID 1, got %d", book.ID)
	}
}

// TestCreateBookMissingTitle verifies validation rejects missing title
func TestCreateBookMissingTitle(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	r := gin.New()
	r.POST("/books", createBook)

	payload := bytes.NewBufferString(`{"author":"Test Author"}`)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("POST", "/books", payload)
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", resp.StatusCode)
	}
}

// TestCreateBookMissingAuthor verifies validation rejects missing author
func TestCreateBookMissingAuthor(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	r := gin.New()
	r.POST("/books", createBook)

	payload := bytes.NewBufferString(`{"title":"Test Book"}`)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("POST", "/books", payload)
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", resp.StatusCode)
	}
}

// TestListBooksAll verifies listing all books returns all records
func TestListBooksAll(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn1")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn2")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Three", "Author A", 2022, "isbn3")

	r := gin.New()
	r.GET("/books", listBooks)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books", nil)
	listBooks(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}
}

// TestListBooksByAuthor verifies filtering by author works
func TestListBooksByAuthor(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn1")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn2")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Three", "Author A", 2022, "isbn3")

	r := gin.New()
	r.GET("/books", listBooks)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books?author=Author%20A", nil)
	listBooks(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if len(books) != 2 {
		t.Errorf("Expected 2 books for Author A, got %d", len(books))
	}
}

// TestGetBookExisting verifies retrieving an existing book
func TestGetBookExisting(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "isbn-test")

	r := gin.New()
	r.GET("/books/:id", getBook)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books/1", nil)
	c.Params = []gin.Param{{Key: "id", Value: "1"}}
	getBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", resp.StatusCode, w.Body.String())
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", book.Title)
	}
}

// TestGetBookNotFound verifies 404 for non-existent book
func TestGetBookNotFound(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	r := gin.New()
	r.GET("/books/:id", getBook)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books/999", nil)
	c.Params = []gin.Param{{Key: "id", Value: "999"}}
	getBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", resp.StatusCode)
	}
}

// TestUpdateBook verifies updating an existing book
func TestUpdateBook(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Old Title", "Old Author", 2020, "old-isbn")

	r := gin.New()
	r.PUT("/books/:id", updateBook)

	payload := bytes.NewBufferString(`{"title":"New Title","author":"New Author","year":2024,"isbn":"new-isbn"}`)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("PUT", "/books/1", payload)
	c.Params = []gin.Param{{Key: "id", Value: "1"}}
	updateBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", resp.StatusCode, w.Body.String())
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Title != "New Title" {
		t.Errorf("Expected title 'New Title', got '%s'", book.Title)
	}
	if book.Author != "New Author" {
		t.Errorf("Expected author 'New Author', got '%s'", book.Author)
	}
}

// TestDeleteBook verifies deleting an existing book
func TestDeleteBook(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author", 2023, "isbn-del")

	r := gin.New()
	r.DELETE("/books/:id", deleteBook)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("DELETE", "/books/1", nil)
	c.Params = []gin.Param{{Key: "id", Value: "1"}}
	deleteBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", resp.StatusCode, w.Body.String())
	}

	var count int
	db.QueryRow("SELECT COUNT(*) FROM books").Scan(&count)
	if count != 0 {
		t.Errorf("Expected 0 books after deletion, got %d", count)
	}
}

// TestDeleteBookNotFound verifies 404 when deleting non-existent book
func TestDeleteBookNotFound(t *testing.T) {
	setupTestDB()
	defer os.Remove("test_books.db")

	r := gin.New()
	r.DELETE("/books/:id", deleteBook)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("DELETE", "/books/999", nil)
	c.Params = []gin.Param{{Key: "id", Value: "999"}}
	deleteBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404 for non-existent book, got %d", resp.StatusCode)
	}
}

// TestInvalidBookID verifies 400 for non-numeric book ID
func TestInvalidBookID(t *testing.T) {
	r := gin.New()
	r.GET("/books/:id", getBook)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/books/abc", nil)
	c.Params = []gin.Param{{Key: "id", Value: "abc"}}
	getBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status 400 for invalid ID, got %d", resp.StatusCode)
	}
}
