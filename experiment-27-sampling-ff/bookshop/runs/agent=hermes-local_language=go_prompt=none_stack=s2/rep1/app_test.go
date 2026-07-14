package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func setupTestDB() (*sql.DB, error) {
	// Remove any existing test database
	os.Remove("./books_test.db")

	var err error
	db, err = sql.Open("sqlite3", "./books_test.db")
	if err != nil {
		return nil, fmt.Errorf("failed to open test database: %w", err)
	}

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return nil, fmt.Errorf("failed to create test table: %w", err)
	}

	return db, nil
}

func teardownTestDB() {
	os.Remove("./books_test.db")
}

func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
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

	return r
}

func TestHealthCheck(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	healthCheck(c)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got '%v'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("failed to setup test db: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	tests := []struct {
		name       string
		body       map[string]interface{}
		wantStatus int
	}{
		{
			name: "valid book",
			body: map[string]interface{}{
				"title":  "The Go Programming Language",
				"author": "Alan Donovan",
				"year":   2015,
				"isbn":   "978-0134190440",
			},
			wantStatus: http.StatusCreated,
		},
		{
			name: "missing title and author",
			body: map[string]interface{}{
				"year": 2015,
				"isbn": "978-0134190440",
			},
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "missing title",
			body: map[string]interface{}{
				"author": "Test Author",
				"year":   2015,
				"isbn":   "978-0134190440",
			},
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "missing author",
			body: map[string]interface{}{
				"title": "Test Title",
				"year":  2015,
				"isbn":  "978-0134190440",
			},
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			body, _ := json.Marshal(tt.body)

			c, _ := gin.CreateTestContext(w)
			c.Request = &http.Request{
				Method: "POST",
				URL:    newURL("/books"),
				Header: http.Header{"Content-Type": []string{"application/json"}},
				Body:   io.NopCloser(bytes.NewReader(body)),
			}

			r.ServeHTTP(w, c.Request)

			if w.Code != tt.wantStatus {
				t.Errorf("expected status %d, got %d. Body: %s", tt.wantStatus, w.Code, w.Body.String())
			}

			if tt.wantStatus == http.StatusCreated {
				var resp Book
				json.Unmarshal(w.Body.Bytes(), &resp)

				if resp.Title != tt.body["title"] {
					t.Errorf("expected title %s, got %s", tt.body["title"], resp.Title)
				}
				if resp.Author != tt.body["author"] {
					t.Errorf("expected author %s, got %s", tt.body["author"], resp.Author)
				}
			}
		})
	}

	// Verify db was used (prevent unused variable warning)
	db.Close()
}

func TestListBooks(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("failed to setup test db: %v", err)
	}
	defer teardownTestDB()

	// Insert test data
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn-1")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn-2")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Three", "Author A", 2022, "isbn-3")

	r := setupTestRouter()

	// Test listing all books
	t.Run("list all books", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "GET",
			URL:    newURL("/books"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)

		if len(books) != 3 {
			t.Errorf("expected 3 books, got %d", len(books))
		}
	})

	// Test filtering by author
	t.Run("filter by author", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "GET",
			URL:    newURL("/books?author=Author%20A"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)

		if len(books) != 2 {
			t.Errorf("expected 2 books for Author A, got %d", len(books))
		}

		for _, b := range books {
			if b.Author != "Author A" {
				t.Errorf("expected author 'Author A', got '%s'", b.Author)
			}
		}
	})

	// Test filtering with no results
	t.Run("filter by non-existent author", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "GET",
			URL:    newURL("/books?author=NonExistent"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)

		if len(books) != 0 {
			t.Errorf("expected 0 books, got %d", len(books))
		}

		if books == nil {
			t.Error("expected empty array, got null")
		}
	})

	// Verify db was used (prevent unused variable warning)
	db.Close()
}

func TestGetBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("failed to setup test db: %v", err)
	}
	defer teardownTestDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "isbn-test")

	r := setupTestRouter()

	t.Run("get existing book", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "GET",
			URL:    newURL("/books/1"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var book Book
		json.Unmarshal(w.Body.Bytes(), &book)

		if book.Title != "Test Book" {
			t.Errorf("expected title 'Test Book', got '%s'", book.Title)
		}
		if book.Author != "Test Author" {
			t.Errorf("expected author 'Test Author', got '%s'", book.Author)
		}
	})

	t.Run("get non-existent book", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "GET",
			URL:    newURL("/books/999"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})

	t.Run("get book with invalid ID", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "GET",
			URL:    newURL("/books/abc"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})

	// Verify db was used (prevent unused variable warning)
	db.Close()
}

func TestUpdateBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("failed to setup test db: %v", err)
	}
	defer teardownTestDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Original Title", "Original Author", 2020, "isbn-original")

	r := setupTestRouter()

	t.Run("update book", func(t *testing.T) {
		newTitle := "Updated Title"
		w := httptest.NewRecorder()
		body, _ := json.Marshal(map[string]interface{}{
			"title":  newTitle,
			"author": "Updated Author",
			"year":   2024,
			"isbn":   "isbn-updated",
		})

		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "PUT",
			URL:    newURL("/books/1"),
			Header: http.Header{"Content-Type": []string{"application/json"}},
			Body:   io.NopCloser(bytes.NewReader(body)),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d. Body: %s", w.Code, w.Body.String())
		}

		var resp Book
		json.Unmarshal(w.Body.Bytes(), &resp)

		if resp.Title != newTitle {
			t.Errorf("expected title '%s', got '%s'", newTitle, resp.Title)
		}
		if resp.Author != "Updated Author" {
			t.Errorf("expected author 'Updated Author', got '%s'", resp.Author)
		}
	})

	t.Run("update non-existent book", func(t *testing.T) {
		w := httptest.NewRecorder()
		body, _ := json.Marshal(map[string]interface{}{
			"title":  "New Title",
			"author": "New Author",
			"year":   2024,
			"isbn":   "isbn-new",
		})

		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "PUT",
			URL:    newURL("/books/999"),
			Header: http.Header{"Content-Type": []string{"application/json"}},
			Body:   io.NopCloser(bytes.NewReader(body)),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})

	t.Run("partial update - only title", func(t *testing.T) {
		w := httptest.NewRecorder()
		body, _ := json.Marshal(map[string]interface{}{
			"title": "Partially Updated",
		})

		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "PUT",
			URL:    newURL("/books/1"),
			Header: http.Header{"Content-Type": []string{"application/json"}},
			Body:   io.NopCloser(bytes.NewReader(body)),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d. Body: %s", w.Code, w.Body.String())
		}

		var resp Book
		json.Unmarshal(w.Body.Bytes(), &resp)

		if resp.Title != "Partially Updated" {
			t.Errorf("expected title 'Partially Updated', got '%s'", resp.Title)
		}

		// Verify other fields are preserved
		if resp.Author != "Updated Author" {
			t.Errorf("expected author 'Updated Author' (preserved), got '%s'", resp.Author)
		}
	})

	// Verify db was used (prevent unused variable warning)
	db.Close()
}

func TestDeleteBook(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("failed to setup test db: %v", err)
	}
	defer teardownTestDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author", 2023, "isbn-delete")

	r := setupTestRouter()

	t.Run("delete existing book", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "DELETE",
			URL:    newURL("/books/1"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var resp map[string]interface{}
		json.Unmarshal(w.Body.Bytes(), &resp)

		if resp["message"] != "book deleted successfully" {
			t.Errorf("expected success message, got '%v'", resp["message"])
		}

		// Verify book is actually deleted
		var count int
		db.QueryRow("SELECT COUNT(*) FROM books WHERE id = 1").Scan(&count)
		if count != 0 {
			t.Error("book should be deleted but still exists")
		}
	})

	t.Run("delete non-existent book", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "DELETE",
			URL:    newURL("/books/999"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})

	t.Run("delete with invalid ID", func(t *testing.T) {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = &http.Request{
			Method: "DELETE",
			URL:    newURL("/books/abc"),
		}

		r.ServeHTTP(w, c.Request)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})

	// Verify db was used (prevent unused variable warning)
	db.Close()
}

func TestEmptyList(t *testing.T) {
	db, err := setupTestDB()
	if err != nil {
		t.Fatalf("failed to setup test db: %v", err)
	}
	defer teardownTestDB()

	r := setupTestRouter()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = &http.Request{
		Method: "GET",
		URL:    newURL("/books"),
	}

	r.ServeHTTP(w, c.Request)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 0 {
		t.Errorf("expected empty list, got %d books", len(books))
	}

	if books == nil {
		t.Error("expected empty array, got null")
	}

	// Verify db was used (prevent unused variable warning)
	db.Close()
}

// newURL creates a URL with the given path for test context.
func newURL(path string) *url.URL {
	u, _ := url.Parse("http://localhost" + path)
	return u
}
