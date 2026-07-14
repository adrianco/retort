package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

// setupTestDB opens an in-memory SQLite database and creates the books table.
func setupTestDB(t *testing.T) func() {
	t.Helper()

	var err error
	db, err = sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatalf("failed to open test database: %v", err)
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
		db.Close()
		t.Fatalf("failed to create test table: %v", err)
	}

	return func() {
		db.Close()
		db = nil
	}
}

// newTestRouter returns a Gin router with all routes attached, using the current db.
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

// --- Tests ---

func TestHealthCheck(t *testing.T) {
	defer setupTestDB(t)()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)

	newTestRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "healthy" {
		t.Errorf("expected status 'healthy', got %v", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	defer setupTestDB(t)()

	tests := []struct {
		name       string
		body       map[string]interface{}
		wantStatus int
	}{
		{
			name: "valid book",
			body: map[string]interface{}{
				"title":  "The Go Programming Language",
				"author": "Donovan & Kernighan",
				"year":   2015,
				"isbn":   "978-0134190440",
			},
			wantStatus: http.StatusCreated,
		},
		{
			name: "missing title",
			body: map[string]interface{}{
				"author": "Test Author",
			},
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "missing author",
			body: map[string]interface{}{
				"title": "Test Title",
			},
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			payload, _ := json.Marshal(tt.body)
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("POST", "/books", bytes.NewReader(payload))
			req.Header.Set("Content-Type", "application/json")

			newTestRouter().ServeHTTP(w, req)

			if w.Code != tt.wantStatus {
				t.Errorf("expected status %d, got %d; body: %s", tt.wantStatus, w.Code, w.Body.String())
			}

			if tt.wantStatus == http.StatusCreated {
				var book Book
				json.Unmarshal(w.Body.Bytes(), &book)
				if book.ID == 0 {
					t.Error("expected non-zero ID for created book")
				}
				if book.Title != tt.body["title"] {
					t.Errorf("expected title %s, got %s", tt.body["title"], book.Title)
				}
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	defer setupTestDB(t)()

	// Insert test data first
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book A", "Author One", 2020, "isbn-1")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book B", "Author Two", 2021, "isbn-2")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book C", "Author One", 2022, "isbn-3")

	// Test: list all
	t.Run("list all books", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books", nil)

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)
		if len(books) != 3 {
			t.Errorf("expected 3 books, got %d", len(books))
		}
	})

	// Test: filter by author
	t.Run("filter by author", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books?author=Author+One", nil)

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)
		if len(books) != 2 {
			t.Errorf("expected 2 books for Author One, got %d", len(books))
		}
		for _, b := range books {
			if b.Author != "Author One" {
				t.Errorf("expected author 'Author One', got '%s'", b.Author)
			}
		}
	})

	// Test: empty result set with filter
	t.Run("empty author filter", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books?author=NonExistent", nil)

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)
		if len(books) != 0 {
			t.Errorf("expected 0 books, got %d", len(books))
		}
	})
}

func TestGetBook(t *testing.T) {
	defer setupTestDB(t)()

	// Insert a book first
	res, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "isbn-test")
	id, _ := res.LastInsertId()

	// Test: get existing book
	t.Run("get existing book", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", fmt.Sprintf("/books/%d", id), nil)

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d; body: %s", w.Code, w.Body.String())
			return
		}

		var book Book
		json.Unmarshal(w.Body.Bytes(), &book)
		if book.Title != "Test Book" {
			t.Errorf("expected title 'Test Book', got '%s'", book.Title)
		}
		if book.ID != int(id) {
			t.Errorf("expected ID %d, got %d", id, book.ID)
		}
	})

	// Test: get non-existent book
	t.Run("get non-existent book", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books/9999", nil)

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})
}

func TestUpdateBook(t *testing.T) {
	defer setupTestDB(t)()

	// Insert a book first
	res, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Original Title", "Original Author", 2020, "isbn-old")
	id, _ := res.LastInsertId()

	// Test: update existing book with all fields
	t.Run("update existing book", func(t *testing.T) {
		payload, _ := json.Marshal(map[string]interface{}{
			"title":  "Updated Title",
			"author": "Updated Author",
			"year":   2024,
			"isbn":   "isbn-new",
		})

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("PUT", fmt.Sprintf("/books/%d", id), bytes.NewReader(payload))
		req.Header.Set("Content-Type", "application/json")

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d; body: %s", w.Code, w.Body.String())
			return
		}

		var book Book
		json.Unmarshal(w.Body.Bytes(), &book)
		if book.Title != "Updated Title" {
			t.Errorf("expected title 'Updated Title', got '%s'", book.Title)
		}
		if book.Author != "Updated Author" {
			t.Errorf("expected author 'Updated Author', got '%s'", book.Author)
		}
	})

	// Test: update non-existent book
	t.Run("update non-existent book", func(t *testing.T) {
		payload, _ := json.Marshal(map[string]interface{}{
			"title": "Nope",
		})

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("PUT", "/books/9999", bytes.NewReader(payload))
		req.Header.Set("Content-Type", "application/json")

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})

	// Test: partial update (only title)
	t.Run("partial update", func(t *testing.T) {
		payload, _ := json.Marshal(map[string]interface{}{
			"title": "Only Title Changed",
		})

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("PUT", fmt.Sprintf("/books/%d", id), bytes.NewReader(payload))
		req.Header.Set("Content-Type", "application/json")

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var book Book
		json.Unmarshal(w.Body.Bytes(), &book)
		if book.Title != "Only Title Changed" {
			t.Errorf("expected title 'Only Title Changed', got '%s'", book.Title)
		}
	})
}

func TestDeleteBook(t *testing.T) {
	defer setupTestDB(t)()

	// Insert a book first
	res, _ := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"ToDelete", "Author", 2023, "isbn-del")
	id, _ := res.LastInsertId()

	// Test: delete existing book
	t.Run("delete existing book", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("DELETE", fmt.Sprintf("/books/%d", id), nil)

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var resp map[string]interface{}
		json.Unmarshal(w.Body.Bytes(), &resp)
		if resp["message"] != "book deleted" {
			t.Errorf("expected message 'book deleted', got %v", resp["message"])
		}

		// Verify it's actually deleted
		var count int
		db.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&count)
		if count != 0 {
			t.Error("book should be deleted but still exists")
		}
	})

	// Test: delete non-existent book
	t.Run("delete non-existent book", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("DELETE", "/books/9999", nil)

		newTestRouter().ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})
}

func TestMain(m *testing.M) {
	os.Remove("books.db")
	code := m.Run()
	os.Exit(code)
}
