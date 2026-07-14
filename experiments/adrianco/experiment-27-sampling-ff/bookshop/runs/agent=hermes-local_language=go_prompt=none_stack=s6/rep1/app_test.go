package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/gin-gonic/gin"
)

func setupTestDB(t *testing.T) *Database {
	t.Helper()
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}
	return db
}

func setupTestRouter(t *testing.T) (*gin.Engine, *Database) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	db := setupTestDB(t)
	router := gin.Default()

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"message": "Book API is running",
		})
	})

	router.POST("/books", func(c *gin.Context) {
		var req CreateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request body: " + err.Error(),
			})
			return
		}

		if req.Title == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Title is required and cannot be empty",
			})
			return
		}
		if req.Author == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Author is required and cannot be empty",
			})
			return
		}

		book, err := db.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusCreated, book)
	})

	router.GET("/books", func(c *gin.Context) {
		author := c.Query("author")
		books, err := db.ListBooks(author)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
			})
			return
		}
		if books == nil {
			books = []Book{}
		}
		c.JSON(http.StatusOK, books)
	})

	router.GET("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		book, err := db.GetBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, book)
	})

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
				"error": "Invalid request body: " + err.Error(),
			})
			return
		}

		book, err := db.UpdateBook(id, req.Title, req.Author, req.Year, req.ISBN)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, book)
	})

	router.DELETE("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		err = db.DeleteBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Book deleted successfully",
		})
	})

	return router, db
}

func TestHealthCheck(t *testing.T) {
	router, _ := setupTestRouter(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	if response["status"] != "healthy" {
		t.Errorf("expected status 'healthy', got %v", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	router, _ := setupTestRouter(t)

	payload := CreateBookRequest{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got %s", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got %s", book.Author)
	}
	if book.Year != 1925 {
		t.Errorf("expected year 1925, got %d", book.Year)
	}
	if book.ISBN != "978-0743273565" {
		t.Errorf("expected isbn '978-0743273565', got %s", book.ISBN)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	router, _ := setupTestRouter(t)

	t.Run("missing title", func(t *testing.T) {
		payload := CreateBookRequest{
			Author: "Test Author",
		}
		body, _ := json.Marshal(payload)

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		router.ServeHTTP(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})

	t.Run("missing author", func(t *testing.T) {
		payload := CreateBookRequest{
			Title: "Test Book",
		}
		body, _ := json.Marshal(payload)

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		router.ServeHTTP(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})
}

func TestListBooks(t *testing.T) {
	router, db := setupTestRouter(t)

	db.CreateBook("1984", "George Orwell", 1949, "978-0451524935")
	db.CreateBook("Animal Farm", "George Orwell", 1945, "978-0451526342")
	db.CreateBook("To Kill a Mockingbird", "Harper Lee", 1960, "978-0061120084")

	t.Run("list all books", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)

		if len(books) != 3 {
			t.Errorf("expected 3 books, got %d", len(books))
		}
	})

	t.Run("filter by author", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books?author=Orwell", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []Book
		json.Unmarshal(w.Body.Bytes(), &books)

		if len(books) != 2 {
			t.Errorf("expected 2 books for author 'Orwell', got %d", len(books))
		}
	})

	t.Run("filter by non-existent author", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books?author=NonExistent", nil)
		router.ServeHTTP(w, req)

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
	router, db := setupTestRouter(t)

	book, _ := db.CreateBook("Dune", "Frank Herbert", 1965, "978-0441172719")

	t.Run("get existing book", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books/"+strconv.Itoa(book.ID), nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}
	})

	t.Run("get non-existent book", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/books/9999", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})
}

func TestUpdateBook(t *testing.T) {
	router, db := setupTestRouter(t)

	book, _ := db.CreateBook("Original Title", "Original Author", 2000, "000-0000000000")

	payload := UpdateBookRequest{
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2020,
		ISBN:   "111-1111111111",
	}
	body, _ := json.Marshal(payload)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", "/books/"+strconv.Itoa(book.ID), bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var updatedBook Book
	json.Unmarshal(w.Body.Bytes(), &updatedBook)

	if updatedBook.Title != "Updated Title" {
		t.Errorf("expected title 'Updated Title', got %s", updatedBook.Title)
	}
	if updatedBook.Author != "Updated Author" {
		t.Errorf("expected author 'Updated Author', got %s", updatedBook.Author)
	}
}

func TestDeleteBook(t *testing.T) {
	router, db := setupTestRouter(t)

	book, _ := db.CreateBook("To Delete", "Test Author", 2020, "000")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/"+strconv.Itoa(book.ID), nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	// Verify it's actually deleted
	_, err := db.GetBook(book.ID)
	if err == nil {
		t.Error("expected book to be deleted, but it still exists")
	}
}
