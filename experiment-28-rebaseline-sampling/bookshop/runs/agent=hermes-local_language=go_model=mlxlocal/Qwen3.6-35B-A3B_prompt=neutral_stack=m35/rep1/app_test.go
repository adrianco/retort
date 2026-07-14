package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"

	"github.com/gin-gonic/gin"
)

var testDB *sql.DB

func setupTestDB() error {
	// Remove old test db
	os.Remove("./test_books.db")

	var err error
	testDB, err = sql.Open("sqlite3", "./test_books.db?_busy_timeout=5000")
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

	_, err = testDB.Exec(createTable)
	if err != nil {
		return err
	}

	return nil
}

func cleanupTestDB() {
	testDB.Exec("DELETE FROM books")
	testDB.Close()
	os.Remove("./test_books.db")
}

func resetTestDB(t *testing.T) {
	t.Helper()
	testDB.Exec("DELETE FROM books")
	// Reset auto-increment
	testDB.Exec("DELETE FROM sqlite_sequence WHERE name='books'")
}

// createRouterWithTestDB creates a gin router that uses the test database
func createRouterWithTestDB() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.Default()

	r.GET("/health", healthHandler)

	books := r.Group("/books")
	{
		books.POST("", func(c *gin.Context) {
			db = testDB
			createBookHandler(c)
		})
		books.GET("", func(c *gin.Context) {
			db = testDB
			listBooksHandler(c)
		})
		books.GET("/:id", func(c *gin.Context) {
			db = testDB
			getBookHandler(c)
		})
		books.PUT("/:id", func(c *gin.Context) {
			db = testDB
			updateBookHandler(c)
		})
		books.DELETE("/:id", func(c *gin.Context) {
			db = testDB
			deleteBookHandler(c)
		})
	}

	return r
}

func TestMain(m *testing.M) {
	if err := setupTestDB(); err != nil {
		panic(err)
	}
	defer cleanupTestDB()
	os.Exit(m.Run())
}

func TestHealthCheck(t *testing.T) {
	r := createRouterWithTestDB()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got '%s'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	payload := `{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}`

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got '%s'", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}
	if book.Year != 1925 {
		t.Errorf("expected year 1925, got %d", book.Year)
	}
	if book.ISBN != "978-0743273565" {
		t.Errorf("expected isbn '978-0743273565', got '%s'", book.ISBN)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	// Missing title
	payload := `{"author":"Test Author"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400 for missing title, got %d", w.Code)
	}

	// Missing author
	payload = `{"title":"Test Title"}`
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400 for missing author, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	// Insert test data
	_, err := testDB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn-1")
	if err != nil {
		t.Fatal(err)
	}
	_, err = testDB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn-2")
	if err != nil {
		t.Fatal(err)
	}

	// List all
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w, req)

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
	req, _ = http.NewRequest("GET", "/books?author=Author+A", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 1 {
		t.Errorf("expected 1 book for author filter, got %d", len(books))
	}
	if books[0].Author != "Author A" {
		t.Errorf("expected author 'Author A', got '%s'", books[0].Author)
	}
}

func TestGetBook(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	// Insert a book first
	result, err := testDB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "test-isbn")
	if err != nil {
		t.Fatal(err)
	}
	id, _ := result.LastInsertId()

	// Get the book
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/"+strconv.Itoa(int(id)), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "Test Book" {
		t.Errorf("expected title 'Test Book', got '%s'", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/9999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	// Insert a book first
	result, err := testDB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Old Title", "Old Author", 2020, "old-isbn")
	if err != nil {
		t.Fatal(err)
	}
	id, _ := result.LastInsertId()

	// Update the book
	payload := `{"title":"New Title","author":"New Author"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/"+strconv.Itoa(int(id)), bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "New Title" {
		t.Errorf("expected title 'New Title', got '%s'", book.Title)
	}
	if book.Author != "New Author" {
		t.Errorf("expected author 'New Author', got '%s'", book.Author)
	}
	// Year and ISBN should be unchanged
	if book.Year != 2020 {
		t.Errorf("expected year 2020, got %d", book.Year)
	}
	if book.ISBN != "old-isbn" {
		t.Errorf("expected isbn 'old-isbn', got '%s'", book.ISBN)
	}
}

func TestDeleteBook(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	// Insert a book first
	result, err := testDB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"ToDelete", "Author", 2020, "isbn")
	if err != nil {
		t.Fatal(err)
	}
	id, _ := result.LastInsertId()

	// Delete the book
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/"+strconv.Itoa(int(id)), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	// Verify it's gone
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books/"+strconv.Itoa(int(id)), nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404 after delete, got %d", w.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	resetTestDB(t)
	r := createRouterWithTestDB()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/9999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404 for non-existent book, got %d", w.Code)
	}
}
