package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

var testDB *Database

func setupTestDB() error {
	os.Remove("test_books.db")

	conn, err := sql.Open("sqlite3", "test_books.db")
	if err != nil {
		return err
	}

	_, err = conn.Exec("PRAGMA journal_mode=WAL")
	if err != nil {
		return err
	}

	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	_, err = conn.Exec(query)
	if err != nil {
		return err
	}

	testDB = &Database{conn: conn}
	return nil
}

func setupTestEnv() {
	gin.SetMode(gin.TestMode)
}

func teardownTestDB() {
	if testDB != nil {
		testDB.Close()
		os.Remove("test_books.db")
	}
}

func newTestRouter() *gin.Engine {
	setupTestEnv()
	router := gin.New()

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "ok",
			"message": "Service is healthy",
		})
	})

	// Create a new book
	router.POST("/books", func(c *gin.Context) {
		var req CreateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request body. 'title' and 'author' are required fields.",
			})
			return
		}

		req.Title = strings.TrimSpace(req.Title)
		if req.Title == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Title cannot be empty",
			})
			return
		}

		req.Author = strings.TrimSpace(req.Author)
		if req.Author == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Author cannot be empty",
			})
			return
		}

		book, err := testDB.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to create book",
			})
			return
		}

		c.JSON(http.StatusCreated, book)
	})

	// List all books with optional author filter
	router.GET("/books", func(c *gin.Context) {
		author := c.Query("author")
		books, err := testDB.GetAllBooks(author)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to retrieve books",
			})
			return
		}

		if books == nil {
			books = []Book{}
		}

		c.JSON(http.StatusOK, gin.H{
			"books": books,
			"count": len(books),
		})
	})

	// Get a single book by ID
	router.GET("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		book, err := testDB.GetBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, book)
	})

	// Update a book
	router.PUT("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		var req UpdateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request body",
			})
			return
		}

		existingBook, err := testDB.GetBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Book not found",
			})
			return
		}

		title := req.Title
		if title == "" {
			title = existingBook.Title
		}
		author := req.Author
		if author == "" {
			author = existingBook.Author
		}
		year := req.Year
		if year == 0 {
			year = existingBook.Year
		}
		isbn := req.ISBN
		if isbn == "" {
			isbn = existingBook.ISBN
		}

		book, err := testDB.UpdateBook(id, title, author, year, isbn)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to update book",
			})
			return
		}

		c.JSON(http.StatusOK, book)
	})

	// Delete a book
	router.DELETE("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		err = testDB.DeleteBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Book deleted successfully",
			"id":      id,
		})
	})

	return router
}

func TestMain(m *testing.M) {
	if err := setupTestDB(); err != nil {
		panic(err)
	}
	defer teardownTestDB()

	os.Exit(m.Run())
}

func TestHealthCheck(t *testing.T) {
	router := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

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
	router := newTestRouter()

	// Clear existing data
	testDB.conn.Exec("DELETE FROM books")

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got '%s'", book.Title)
	}
	if book.Author != "Alan Donovan" {
		t.Errorf("expected author 'Alan Donovan', got '%s'", book.Author)
	}
	if book.Year != 2015 {
		t.Errorf("expected year 2015, got %d", book.Year)
	}
	if book.ISBN != "978-0134190440" {
		t.Errorf("expected isbn '978-0134190440', got '%s'", book.ISBN)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	router := newTestRouter()

	// Test missing title and author
	body, _ := json.Marshal(CreateBookRequest{})

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400 for missing fields, got %d", w.Code)
	}
}

func TestGetAllBooks(t *testing.T) {
	router := newTestRouter()

	// Clear existing data
	testDB.conn.Exec("DELETE FROM books")

	// Insert test data
	testDB.CreateBook("Book One", "Author A", 2020, "isbn-1")
	testDB.CreateBook("Book Two", "Author B", 2021, "isbn-2")
	testDB.CreateBook("Book Three", "Author A", 2022, "isbn-3")

	// Test without filter
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)

	books := resp["books"].([]interface{})
	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}

	// Test with author filter
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/books?author=Author+A", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	json.Unmarshal(w.Body.Bytes(), &resp)
	books = resp["books"].([]interface{})
	if len(books) != 2 {
		t.Errorf("expected 2 books for author 'Author A', got %d", len(books))
	}
}

func TestGetBookByID(t *testing.T) {
	router := newTestRouter()

	// Insert a test book
	book, _ := testDB.CreateBook("Test Book", "Test Author", 2023, "isbn-test")

	w := httptest.NewRecorder()
	url := "/books/" + strconv.Itoa(book.ID)
	req, _ := http.NewRequest("GET", url, nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var result Book
	json.Unmarshal(w.Body.Bytes(), &result)

	if result.Title != "Test Book" {
		t.Errorf("expected title 'Test Book', got '%s'", result.Title)
	}
	if result.Author != "Test Author" {
		t.Errorf("expected author 'Test Author', got '%s'", result.Author)
	}
}

func TestGetBookNotFound(t *testing.T) {
	router := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/9999", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	router := newTestRouter()

	// Insert a test book
	book, _ := testDB.CreateBook("Original Title", "Original Author", 2020, "isbn-orig")

	newTitle := "Updated Title"
	newAuthor := "Updated Author"
	newYear := 2024
	newISBN := "isbn-updated"

	reqBody, _ := json.Marshal(UpdateBookRequest{
		Title:  newTitle,
		Author: newAuthor,
		Year:   newYear,
		ISBN:   newISBN,
	})

	w := httptest.NewRecorder()
	url := "/books/" + strconv.Itoa(book.ID)
	req, _ := http.NewRequest("PUT", url, bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var result Book
	json.Unmarshal(w.Body.Bytes(), &result)

	if result.Title != newTitle {
		t.Errorf("expected title '%s', got '%s'", newTitle, result.Title)
	}
	if result.Author != newAuthor {
		t.Errorf("expected author '%s', got '%s'", newAuthor, result.Author)
	}
	if result.Year != newYear {
		t.Errorf("expected year %d, got %d", newYear, result.Year)
	}
	if result.ISBN != newISBN {
		t.Errorf("expected isbn '%s', got '%s'", newISBN, result.ISBN)
	}
}

func TestDeleteBook(t *testing.T) {
	router := newTestRouter()

	// Insert a test book
	book, _ := testDB.CreateBook("To Delete", "Author", 2023, "isbn-del")

	w := httptest.NewRecorder()
	url := "/books/" + strconv.Itoa(book.ID)
	req, _ := http.NewRequest("DELETE", url, nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	// Verify it's deleted
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", url, nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404 after delete, got %d", w.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	router := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/9999", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestInvalidBookID(t *testing.T) {
	router := newTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/abc", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400 for invalid ID, got %d", w.Code)
	}
}
