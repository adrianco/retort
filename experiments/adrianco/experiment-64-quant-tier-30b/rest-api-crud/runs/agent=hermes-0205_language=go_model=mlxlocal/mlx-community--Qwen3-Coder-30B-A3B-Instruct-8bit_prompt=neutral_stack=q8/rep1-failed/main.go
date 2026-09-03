package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/sqlite"
)

type Book struct {
	ID     uint   `json:"id" gorm:"primary_key"`
	Title  string `json:"title" gorm:"not null"`
	Author string `json:"author" gorm:"not null"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookRequest struct {
	Title  string `json:"title" binding:"required"`
	Author string `json:"author" binding:"required"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookUpdateRequest struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

var database *gorm.DB

func initDB() {
	var err error
	database, err = gorm.Open("sqlite3", "books.db")
	if err != nil {
		log.Fatal("Failed to connect database:", err)
	}
	
	// Migrate the schema
	database.AutoMigrate(&Book{})
}

func main() {
	initDB()
	defer database.Close()

	// Create a Gin router
	r := gin.Default()

	// Health check endpoint
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})

	// Create a new book
	r.POST("/books", func(c *gin.Context) {
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

		database.Create(&book)
		c.JSON(http.StatusCreated, book)
	})

	// List all books with optional author filter
	r.GET("/books", func(c *gin.Context) {
		var books []Book
		author := c.Query("author")
			
		if author != "" {
			database.Where("author = ?", author).Find(&books)
		} else {
			database.Find(&books)
		}
			
		c.JSON(http.StatusOK, books)
	})

	// Get a single book by ID
	r.GET("/books/:id", func(c *gin.Context) {
		id := c.Param("id")
		var book Book
			
		if err := database.Where("id = ?", id).First(&book).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
			return
		}
			
		c.JSON(http.StatusOK, book)
	})

	// Update a book
	r.PUT("/books/:id", func(c *gin.Context) {
		id := c.Param("id")
		var book Book
			
		if err := database.Where("id = ?", id).First(&book).Error; err != nil {
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

		database.Save(&book)
		c.JSON(http.StatusOK, book)
	})

	// Delete a book
	r.DELETE("/books/:id", func(c *gin.Context) {
		id := c.Param("id")
		var book Book
			
		if err := database.Where("id = ?", id).First(&book).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
			return
		}
			
		database.Delete(&book)
		c.JSON(http.StatusOK, gin.H{"message": "Book deleted successfully"})
	})

	// Start the server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	
	log.Printf("Server starting on port %s", port)
	r.Run(":" + port)
}