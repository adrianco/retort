package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in our collection
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput represents the input for creating/updating a book
type BookInput struct {
	Title  string `json:"title" binding:"required"`
	Author string `json:"author" binding:"required"`
	Year   int    `json:"year" binding:"required"`
	ISBN   string `json:"isbn" binding:"required"`
}

// HealthCheckResponse represents the health check response
type HealthCheckResponse struct {
	Status    string `json:"status"`
	Timestamp string `json:"timestamp"`
	Database  string `json:"database"`
}

var db *sql.DB

// Initialize database connection
func initDB() error {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		return err
	}

	// Create table if it doesn't exist
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return err
	}

	return nil
}

// CreateBook handles POST /books - Create a new book
func CreateBook(c *gin.Context) {
	var input BookInput

	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid input: " + err.Error(),
		})
		return
	}

	// Validation: title and author are required
	if input.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Title is required",
		})
		return
	}

	if input.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Author is required",
		})
		return
	}

	insertSQL := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := db.Exec(insertSQL, input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create book: " + err.Error(),
		})
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to get book ID: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"id":     id,
		"title":  input.Title,
		"author": input.Author,
		"year":   input.Year,
		"isbn":   input.ISBN,
	})
}

// GetBooks handles GET /books - List all books with optional author filter
func GetBooks(c *gin.Context) {
	author := c.Query("author")

	var books []Book

	if author != "" {
		// Filter by author
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to query books: " + err.Error(),
			})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var book Book
			err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{
					"error": "Failed to scan book: " + err.Error(),
				})
				return
			}
			books = append(books, book)
		}
	} else {
		// Get all books
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to query books: " + err.Error(),
			})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var book Book
			err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{
					"error": "Failed to scan book: " + err.Error(),
				})
				return
			}
			books = append(books, book)
		}
	}

	c.JSON(http.StatusOK, books)
}

// GetBook handles GET /books/{id} - Get a single book by ID
func GetBook(c *gin.Context) {
	id := c.Param("id")

	bookID, err := strconv.ParseInt(id, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid book ID",
		})
		return
	}

	var book Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", bookID).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Book not found",
		})
		return
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to query book: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, book)
}

// UpdateBook handles PUT /books/{id} - Update a book
func UpdateBook(c *gin.Context) {
	id := c.Param("id")

	bookID, err := strconv.ParseInt(id, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid book ID",
		})
		return
	}

	// Check if book exists
	var existing Book
	err = db.QueryRow("SELECT id FROM books WHERE id = ?", bookID).Scan(&existing.ID)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Book not found",
		})
		return
	}

	var input BookInput

	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid input: " + err.Error(),
		})
		return
	}

	// Validation: title and author are required
	if input.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Title is required",
		})
		return
	}

	if input.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Author is required",
		})
		return
	}

	updateSQL := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err = db.Exec(updateSQL, input.Title, input.Author, input.Year, input.ISBN, bookID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update book: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"id":     bookID,
		"title":  input.Title,
		"author": input.Author,
		"year":   input.Year,
		"isbn":   input.ISBN,
	})
}

// DeleteBook handles DELETE /books/{id} - Delete a book
func DeleteBook(c *gin.Context) {
	id := c.Param("id")

	bookID, err := strconv.ParseInt(id, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid book ID",
		})
		return
	}

	// Check if book exists
	var existing Book
	err = db.QueryRow("SELECT id FROM books WHERE id = ?", bookID).Scan(&existing.ID)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Book not found",
		})
		return
	}

	deleteSQL := `DELETE FROM books WHERE id = ?`
	_, err = db.Exec(deleteSQL, bookID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to delete book: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Book deleted successfully",
	})
}

// HealthCheck handles GET /health - Health check endpoint
func HealthCheck(c *gin.Context) {
	response := HealthCheckResponse{
		Status:    "healthy",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Database:  "connected",
	}

	c.JSON(http.StatusOK, response)
}

func main() {
	// Initialize database
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	// Create gin router
	r := gin.Default()

	// API routes
	api := r.Group("/api")
	{
		// Health check
		api.GET("/health", HealthCheck)

		// Books endpoints
		api.GET("/books", GetBooks)
		api.POST("/books", CreateBook)
		api.GET("/books/:id", GetBook)
		api.PUT("/books/:id", UpdateBook)
		api.DELETE("/books/:id", DeleteBook)
	}

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
