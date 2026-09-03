package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/sqlite"
)

func setupTestDB() *gorm.DB {
	db, err := gorm.Open("sqlite3", ":memory:")
	if err != nil {
		panic("failed to connect database")
	}
	db.AutoMigrate(&Book{})
	return db
}

func setupTestRouter(db *gorm.DB) *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	
	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})

	// Create a new book
	router.POST("/books", func(c *gin.Context) {
		var bookReq BookRequest
		if err := c.ShouldBindJSON(&bookReq); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		book := Book{
			Title:  bookReq.Title,
			Author: bookReq.Author,
			Year:   bookReq.Year,
			ISBN:   bookReq.ISBN,
		}

		db.Create(&book)
		c.JSON(http.StatusCreated, book)
	})

	// List all books with optional author filter
	router.GET("/books", func(c *gin.Context) {
		var books []Book
		author := c.Query("author")
		
		if author != "" {
			db.Where("author = ?", author).Find(&books)
		} else {
			db.Find(&books)
		}
		
		c.JSON(http.StatusOK, books)
	})

	// Get a single book by ID
	router.GET("/books/:id", func(c *gin.Context) {
		id := c.Param("id")
		var book Book
		
		if err := db.Where("id = ?", id).First(&book).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
			return
		}
		
		c.JSON(http.StatusOK, book)
	})

	// Update a book
	router.PUT("/books/:id", func(c *gin.Context) {
		id := c.Param("id")
		var book Book
		
		if err := db.Where("id = ?", id).First(&book).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
			return
		}

		var bookUpdateReq BookUpdateRequest
		if err := c.ShouldBindJSON(&bookUpdateReq); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Update only provided fields
		if bookUpdateReq.Title != nil {
			book.Title = *bookUpdateReq.Title
		}
		if bookUpdateReq.Author != nil {
			book.Author = *bookUpdateReq.Author
		}
		if bookUpdateReq.Year != nil {
			book.Year = *bookUpdateReq.Year
		}
		if bookUpdateReq.ISBN != nil {
			book.ISBN = *bookUpdateReq.ISBN
		}

		db.Save(&book)
		c.JSON(http.StatusOK, book)
	})

	// Delete a book
	router.DELETE("/books/:id", func(c *gin.Context) {
		id := c.Param("id")
		var book Book
		
		if err := db.Where("id = ?", id).First(&book).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
			return
		}
		
		db.Delete(&book)
		c.JSON(http.StatusOK, gin.H{"message": "Book deleted successfully"})
	})
	
	return router
}

func TestHealthCheck(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatal(err)
	}

	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%v'", response["status"])
	}
}

func TestCreateBook(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	bookData := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Expected status code %d, got %d", http.StatusCreated, w.Code)
	}

	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatal(err)
	}

	if response.Title != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%s'", response.Title)
	}

	if response.Author != "Alan A. A. Donovan" {
		t.Errorf("Expected author 'Alan A. A. Donovan', got '%s'", response.Author)
	}

	if response.Year != 2015 {
		t.Errorf("Expected year 2015, got %d", response.Year)
	}

	if response.ISBN != "978-0134190440" {
		t.Errorf("Expected ISBN '978-0134190440', got '%s'", response.ISBN)
	}
}

func TestCreateBookMissingRequiredFields(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	bookData := map[string]interface{}{
		"title": "The Go Programming Language",
		// Missing author field
		"year": 2015,
	}

	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestGetAllBooks(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	// Create a book first
	bookData := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Now test getting all books
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response []Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatal(err)
	}

	if len(response) != 1 {
		t.Errorf("Expected 1 book, got %d", len(response))
	}
}

func TestGetBookById(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	// Create a book first
	bookData := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Get the book by ID (should be 1)
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatal(err)
	}

	if response.Title != "The Go Programming Language" {
		t.Errorf("Expected title 'The Go Programming Language', got '%s'", response.Title)
	}
}

func TestGetNonExistentBook(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	req := httptest.NewRequest("GET", "/books/999", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status code %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	// Create a book first
	bookData := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Update the book
	updateData := map[string]interface{}{
		"title": "The Go Programming Language (Updated)",
		"year":  2020,
	}
	jsonData, _ = json.Marshal(updateData)
	req = httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatal(err)
	}

	if response.Title != "The Go Programming Language (Updated)" {
		t.Errorf("Expected updated title 'The Go Programming Language (Updated)', got '%s'", response.Title)
	}

	if response.Year != 2020 {
		t.Errorf("Expected updated year 2020, got %d", response.Year)
	}
}

func TestDeleteBook(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	// Create a book first
	bookData := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	jsonData, _ := json.Marshal(bookData)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Delete the book
	req = httptest.NewRequest("DELETE", "/books/1", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	// Try to get the deleted book
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status code %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestFilterBooksByAuthor(t *testing.T) {
	db := setupTestDB()
	defer db.Close()
	router := setupTestRouter(db)
	
	// Create two books with different authors
	book1Data := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan A. A. Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}
	book2Data := map[string]interface{}{
		"title":  "Learning Go",
		"author": "Jon Bodner",
		"year":   2019,
		"isbn":   "978-0134190441",
	}

	jsonData, _ := json.Marshal(book1Data)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	jsonData, _ = json.Marshal(book2Data)
	req = httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Filter by author
	req = httptest.NewRequest("GET", "/books?author=Alan%20A.%20A.%20Donovan", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response []Book
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatal(err)
	}

	if len(response) != 1 {
		t.Errorf("Expected 1 book for author, got %d", len(response))
	}

	if response[0].Author != "Alan A. A. Donovan" {
		t.Errorf("Expected author 'Alan A. A. Donovan', got '%s'", response[0].Author)
	}
}