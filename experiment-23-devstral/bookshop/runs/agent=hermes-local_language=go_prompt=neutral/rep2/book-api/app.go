package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "gorm.io/driver/sqlite"
    "gorm.io/gorm"
    "gorm.io/gorm/logger"
    "strconv"
)

type Book struct {
    ID     uint   `json:"id" gorm:"primaryKey"`
    Title  string `json:"title" binding:"required"`
    Author string `json:"author" binding:"required"`
    Year   int    `json:"year"`
    ISBN   string `json:"isbn"`
}

var db *gorm.DB
var err error

func main() {
    // Initialize Gin
    r := gin.Default()
    
    // Initialize database
    db, err = gorm.Open(sqlite.Open("books.db"), &gorm.Config{
        Logger: logger.Default.LogMode(logger.Info),
    })
    
    if err != nil {
        panic("failed to connect to database")
    }
    
    // Auto migrate database schema
    db.AutoMigrate(&Book{})
    
    // Setup routes
    r.POST("/books", createBook)
    r.GET("/books", getBooks)
    r.GET("/books/:id", getBook)
    r.PUT("/books/:id", updateBook)
    r.DELETE("/books/:id", deleteBook)
    r.GET("/health", healthCheck)
    
    // Start the server
    r.Run(":8080")
}

func createBook(c *gin.Context) {
    var book Book
    if err := c.ShouldBindJSON(&book); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    if err := db.Create(&book).Error; err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusCreated, book)
}

func getBooks(c *gin.Context) {
    var books []Book
    author := c.Query("author")
    
    if author != "" {
        db.Where("author = ?", author).Find(&books)
    } else {
        db.Find(&books)
    }
    
    c.JSON(http.StatusOK, books)
}

func getBook(c *gin.Context) {
    id, err := strconv.Atoi(c.Param("id"))
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
        return
    }
    
    var book Book
    if err := db.First(&book, id).Error; err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
        return
    }
    
    c.JSON(http.StatusOK, book)
}

func updateBook(c *gin.Context) {
    id, err := strconv.Atoi(c.Param("id"))
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
        return
    }
    
    var book Book
    if err := db.First(&book, id).Error; err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
        return
    }
    
    if err := c.ShouldBindJSON(&book); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    if err := db.Save(&book).Error; err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, book)
}

func deleteBook(c *gin.Context) {
    id, err := strconv.Atoi(c.Param("id"))
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
        return
    }
    
    var book Book
    if err := db.Delete(&book, id).Error; err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusNoContent, gin.H{"result": "Book deleted"})
}

func healthCheck(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{"status": "healthy"})
}
