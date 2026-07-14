package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in the collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// CreateBookRequest represents the request body for creating a book
type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// UpdateBookRequest represents the request body for updating a book
type UpdateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var db *sql.DB

// initDB initializes the SQLite database and creates the books table
func initDB() error {
	return initDBWithPath("./books.db")
}

// initDBWithPath initializes the SQLite database at a given path and creates the books table
func initDBWithPath(path string) error {
	var err error
	db, err = sql.Open("sqlite3", path)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	createTableSQL := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	log.Println("Database initialized successfully")
	return nil
}

// healthCheck handles GET /health
func healthCheck(c *gin.Context) {
	if db == nil {
		c.JSON(503, gin.H{"error": "Database not available"})
		return
	}

	if err := db.Ping(); err != nil {
		c.JSON(503, gin.H{"error": "Database not reachable"})
		return
	}

	c.JSON(200, gin.H{"status": "healthy"})
}

// createBook handles POST /books
func createBook(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON body"})
		return
	}

	// Input validation: title and author are required
	if req.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Title is required"})
		return
	}
	if req.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Author is required"})
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create book"})
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get book ID"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"id":     id,
		"title":  req.Title,
		"author": req.Author,
		"year":   req.Year,
		"isbn":   req.ISBN,
	})
}

// listBooks handles GET /books with optional ?author= filter
func listBooks(c *gin.Context) {
	authorFilter := c.Query("author")

	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", authorFilter)
	} else {
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query books"})
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to scan book row"})
			return
		}
		books = append(books, b)
	}

	if books == nil {
		books = []Book{}
	}

	c.JSON(http.StatusOK, books)
}

// getBook handles GET /books/:id
func getBook(c *gin.Context) {
	id := c.Param("id")

	var b Book
	err := db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query book"})
		return
	}

	c.JSON(http.StatusOK, b)
}

// updateBook handles PUT /books/:id
func updateBook(c *gin.Context) {
	id := c.Param("id")

	var req UpdateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON body"})
		return
	}

	// Input validation: title and author are required
	if req.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Title is required"})
		return
	}
	if req.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Author is required"})
		return
	}

	// Check if book exists
	var existingBook Book
	err := db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query book"})
		return
	}

	_, err = db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		req.Title, req.Author, req.Year, req.ISBN, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update book"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"id":     id,
		"title":  req.Title,
		"author": req.Author,
		"year":   req.Year,
		"isbn":   req.ISBN,
	})
}

// deleteBook handles DELETE /books/:id
func deleteBook(c *gin.Context) {
	id := c.Param("id")

	// Check if book exists
	var existingBook Book
	err := db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query book"})
		return
	}

	_, err = db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete book"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Book deleted successfully"})
}

// setupRouter creates and configures the Gin router with all routes
func setupRouter() *gin.Engine {
	gin.SetMode(gin.ReleaseMode)

	r := gin.Default()

	// Health check endpoint
	r.GET("/health", healthCheck)

	// Books API routes
	r.POST("/books", createBook)
	r.GET("/books", listBooks)
	r.GET("/books/:id", getBook)
	r.PUT("/books/:id", updateBook)
	r.DELETE("/books/:id", deleteBook)

	return r
}

func main() {
	// Initialize database
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	r := setupRouter()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Starting server on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
