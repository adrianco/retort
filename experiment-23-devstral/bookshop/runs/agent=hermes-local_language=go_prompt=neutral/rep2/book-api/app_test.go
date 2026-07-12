package main

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"
    "github.com/gin-gonic/gin"
    "gorm.io/driver/sqlite"
    "gorm.io/gorm"
)

type TestBook struct {
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year"`
    ISBN   string `json:"isbn"`
}

func setupRouter() *gin.Engine {
    r := gin.Default()
    db, _ := gorm.Open(sqlite.Open("test_books.db"), &gorm.Config{})
    db.AutoMigrate(&Book{})
    
    // Override the db variable in the global scope for testing
    dbInstance := db
    
    // Create a new router with test database
    r.POST("/books", func(c *gin.Context) {
        var book Book
        if err := c.ShouldBindJSON(&book); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        
        if err := dbInstance.Create(&book).Error; err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        
        c.JSON(http.StatusCreated, book)
    })
    
    r.GET("/books", func(c *gin.Context) {
        var books []Book
        author := c.Query("author")
        
        if author != "" {
            dbInstance.Where("author = ?", author).Find(&books)
        } else {
            dbInstance.Find(&books)
        }
        
        c.JSON(http.StatusOK, books)
    })
    
    r.GET("/books/:id", func(c *gin.Context) {
        id := c.Param("id")
        
        var book Book
        if err := dbInstance.First(&book, id).Error; err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
            return
        }
        
        c.JSON(http.StatusOK, book)
    })
    
    r.PUT("/books/:id", func(c *gin.Context) {
        id := c.Param("id")
        
        var book Book
        if err := dbInstance.First(&book, id).Error; err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
            return
        }
        
        if err := c.ShouldBindJSON(&book); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        
        if err := dbInstance.Save(&book).Error; err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        
        c.JSON(http.StatusOK, book)
    })
    
    r.DELETE("/books/:id", func(c *gin.Context) {
        id := c.Param("id")
        
        if err := dbInstance.Delete(&Book{}, id).Error; err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        
        c.JSON(http.StatusNoContent, gin.H{"result": "Book deleted"})
    })
    
    r.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{"status": "healthy"})
    })
    
    return r
}

func TestCreateBook(t *testing.T) {
    r := setupRouter()
    w := httptest.NewRecorder()
    
    book := TestBook{
        Title:  "Test Book",
        Author: "Test Author",
        Year:   2023,
        ISBN:   "1234567890",
    }
    
    body, _ := json.Marshal(book)
    req, _ := http.NewRequest("POST", "/books", bytes.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    
    r.ServeHTTP(w, req)
    
    if w.Code != http.StatusCreated {
        t.Errorf("Expected status code %d but got %d", http.StatusCreated, w.Code)
    }
    
    var response map[string]interface{}
    json.Unmarshal(w.Body.Bytes(), &response)
    
    if response["title"] != book.Title {
        t.Errorf("Expected title %s but got %s", book.Title, response["title"])
    }
    if response["author"] != book.Author {
        t.Errorf("Expected author %s but got %s", book.Author, response["author"])
    }
}

func TestGetBooks(t *testing.T) {
    r := setupRouter()
    w := httptest.NewRecorder()
    
    // First create a book
    book := TestBook{
        Title:  "Test Book",
        Author: "Test Author",
        Year:   2023,
        ISBN:   "1234567890",
    }
    
    body, _ := json.Marshal(book)
    req, _ := http.NewRequest("POST", "/books", bytes.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    
    r.ServeHTTP(w, req)
    
    // Now get books
    req, _ = http.NewRequest("GET", "/books", nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, req)
    
    if w.Code != http.StatusOK {
        t.Errorf("Expected status code %d but got %d", http.StatusOK, w.Code)
    }
    
    var response []map[string]interface{}
    json.Unmarshal(w.Body.Bytes(), &response)
    
    if len(response) == 0 {
        t.Errorf("Expected at least one book but got %d", len(response))
    }
}

func TestHealthCheck(t *testing.T) {
    r := setupRouter()
    w := httptest.NewRecorder()
    
    req, _ := http.NewRequest("GET", "/health", nil)
    r.ServeHTTP(w, req)
    
    if w.Code != http.StatusOK {
        t.Errorf("Expected status code %d but got %d", http.StatusOK, w.Code)
    }
    
    var response map[string]interface{}
    json.Unmarshal(w.Body.Bytes(), &response)
    
    if response["status"] != "healthy" {
        t.Errorf("Expected status 'healthy' but got %s", response["status"])
    }
}
