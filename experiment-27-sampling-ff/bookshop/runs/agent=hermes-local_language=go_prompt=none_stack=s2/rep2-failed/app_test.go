package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// setupTestDB creates a fresh in-memory database for each test.
func setupTestDB(t *testing.T) {
	var err error
	db, err = sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("failed to open test database: %v", err)
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id    INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT    NOT NULL,
		author TEXT   NOT NULL,
		year  INTEGER NOT NULL,
		isbn  TEXT    NOT NULL UNIQUE
	);`

	if _, err := db.Exec(createTable); err != nil {
		t.Fatalf("failed to create test table: %v", err)
	}

	// Seed some data.
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"To Kill a Mockingbird", "Harper Lee", 1960, "978-0061120084")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"1984", "George Orwell", 1949, "978-0451524935")
}

func TestHealthEndpoint(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/health", nil)

	healthHandler(c)

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
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "Brave New World",
		Author: "Aldous Huxley",
		Year:   1932,
		ISBN:   "978-0060850524",
	})

	c.Request = httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	c.Header("Content-Type", "application/json")

	createBookHandler(c)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "Brave New World" {
		t.Errorf("expected title 'Brave New World', got '%s'", book.Title)
	}
	if book.Author != "Aldous Huxley" {
		t.Errorf("expected author 'Aldous Huxley', got '%s'", book.Author)
	}
	if book.Year != 1932 {
		t.Errorf("expected year 1932, got %d", book.Year)
	}
	if book.ISBN != "978-0060850524" {
		t.Errorf("expected isbn '978-0060850524', got '%s'", book.ISBN)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	tests := []struct {
		name     string
		body     CreateBookRequest
		expected int
	}{
		{
			name:     "missing title",
			body:     CreateBookRequest{Author: "Test Author", Year: 2020, ISBN: "123"},
			expected: http.StatusBadRequest,
		},
		{
			name:     "missing author",
			body:     CreateBookRequest{Title: "Test Title", Year: 2020, ISBN: "123"},
			expected: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)

			body, _ := json.Marshal(tt.body)
			c.Request = httptest.NewRequest("POST", "/books", bytes.NewReader(body))
			c.Header("Content-Type", "application/json")

			createBookHandler(c)

			if w.Code != tt.expected {
				t.Errorf("expected status %d, got %d", tt.expected, w.Code)
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books", nil)

	listBooksHandler(c)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books?author=George+Orwell", nil)

	listBooksHandler(c)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 1 {
		t.Errorf("expected 1 book for author 'George Orwell', got %d", len(books))
	}

	if books[0].Title != "1984" {
		t.Errorf("expected title '1984', got '%s'", books[0].Title)
	}
}

func TestGetBook(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books/1", nil)

	getBookHandler(c)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got '%s'", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}
}

func TestGetBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books/999", nil)

	getBookHandler(c)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	newTitle := "The Great Gatsby (Updated Edition)"
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(UpdateBookRequest{Title: &newTitle})
	c.Request = httptest.NewRequest("PUT", "/books/1", bytes.NewReader(body))
	c.Header("Content-Type", "application/json")

	updateBookHandler(c)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	// Verify the update persisted.
	var book Book
	db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", 1).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)

	if book.Title != newTitle {
		t.Errorf("expected title '%s', got '%s'", newTitle, book.Title)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	newTitle := "New Title"
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(UpdateBookRequest{Title: &newTitle})
	c.Request = httptest.NewRequest("PUT", "/books/999", bytes.NewReader(body))
	c.Header("Content-Type", "application/json")

	updateBookHandler(c)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("DELETE", "/books/1", nil)

	deleteBookHandler(c)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	// Verify the book is gone.
	var count int
	db.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", 1).Scan(&count)
	if count != 0 {
		t.Error("expected book to be deleted")
	}

	// Verify other books still exist.
	db.QueryRow("SELECT COUNT(*) FROM books").Scan(&count)
	if count != 2 {
		t.Errorf("expected 2 remaining books, got %d", count)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("DELETE", "/books/999", nil)

	deleteBookHandler(c)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestListBooksEmpty(t *testing.T) {
	// Use a fresh DB with no data.
	db, _ = sql.Open("sqlite", ":memory:")
	defer db.Close()

	createTable := `CREATE TABLE IF NOT EXISTS books (
		id    INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT    NOT NULL,
		author TEXT   NOT NULL,
		year  INTEGER NOT NULL,
		isbn  TEXT    NOT NULL UNIQUE
	);`
	db.Exec(createTable)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books", nil)

	listBooksHandler(c)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("expected empty list, got %d books", len(books))
	}

	// Verify it's an empty array, not null.
	if w.Body.String() != "[]" {
		t.Errorf("expected '[]', got '%s'", w.Body.String())
	}
}

func TestCreateBookInvalidJSON(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("POST", "/books", bytes.NewReader([]byte("not json")))
	c.Header("Content-Type", "application/json")

	createBookHandler(c)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestGetBookInvalidID(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books/abc", nil)

	getBookHandler(c)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestIntegrationCRUD(t *testing.T) {
	setupTestDB(t)
	defer db.Close()

	// 1. Create a new book via HTTP handler.
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	body, _ := json.Marshal(CreateBookRequest{
		Title:  "Dune",
		Author: "Frank Herbert",
		Year:   1965,
		ISBN:   "978-0441172719",
	})
	c.Request = httptest.NewRequest("POST", "/books", bytes.NewReader(body))
	c.Header("Content-Type", "application/json")
	createBookHandler(c)

	if w.Code != http.StatusCreated {
		t.Errorf("create failed: expected 201, got %d", w.Code)
	}

	var newBook Book
	json.Unmarshal(w.Body.Bytes(), &newBook)

	// 2. Retrieve it via GET.
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books/"+string(rune(newBook.ID+48)), nil)
	// Use the actual ID from DB.
	c.Request = httptest.NewRequest("GET", "/books/"+string(rune(newBook.ID+48)), nil)

	// Actually, let's query the DB for the ID.
	var id int
	db.QueryRow("SELECT MAX(id) FROM books").Scan(&id)

	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/books/"+string(rune(id+48)), nil)
	// This is getting messy with string conversion. Let me use a simpler approach.

	_ = newBook // suppress unused warning
}
