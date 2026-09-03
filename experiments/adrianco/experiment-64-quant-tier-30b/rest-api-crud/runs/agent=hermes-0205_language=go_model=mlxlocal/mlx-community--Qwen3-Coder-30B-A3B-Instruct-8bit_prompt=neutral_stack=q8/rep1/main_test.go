package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/sqlite"
)

var db *gorm.DB
var router *gin.Engine

func setupTestDB() {
	var err error
	db, err = gorm.Open("sqlite3", ":memory:")
	if err != nil {
		panic("failed to connect database")
	}
	db.AutoMigrate(&Book{})
}

func setupTestRouter() {
	gin.SetMode(gin.TestMode)
	router = gin.New()
	
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
}

func TestMain(m *testing.M) {
	setupTestDB()
	setupTestRouter()
	
	code := m.Run()
	
	// Clean up
	db.Close()
	os.Exit(code)
}

func TestHealthCheck(t *testing.T) {
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