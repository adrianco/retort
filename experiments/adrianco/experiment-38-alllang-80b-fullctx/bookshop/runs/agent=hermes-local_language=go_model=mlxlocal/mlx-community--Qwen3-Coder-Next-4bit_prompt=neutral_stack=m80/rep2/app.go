package main

import (
	"database/sql"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in the collection
type Book struct {
	ID      int       `json:"id"`
	Title   string    `json:"title"`
	Author  string    `json:"author"`
	Year    int       `json:"year"`
	ISBN    string    `json:"isbn"`
	Created time.Time `json:"created"`
	Updated time.Time `json:"updated"`
}

// BookInput represents the input for creating/updating a book
type BookInput struct {
	Title  string `json:"title" binding:"required,min=1"`
	Author string `json:"author" binding:"required,min=1"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error string `json:"error"`
}

// HealthResponse represents a health check response
type HealthResponse struct {
	Status string `json:"status"`
}

var db *sql.DB

func main() {
	var err error
	db, err = sql.Open("sqlite3", "books.db")
	if err != nil {
		fmt.Printf("Failed to connect to database: %v\n", err)
		return
	}
	defer db.Close()

	// Create books table if it doesn't exist
	createTable()

	r := gin.Default()

	// Health check endpoint
	r.GET("/health", healthCheck)

	// Books endpoints
	books := r.Group("/books")
	{
		books.GET("", listBooks)
		books.POST("", createBook)
		books.GET("/:id", getBook)
		books.PUT("/:id", updateBook)
		books.DELETE("/:id", deleteBook)
	}

	r.Run(":8080")
}

func createTable() {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT,
		created DATETIME DEFAULT CURRENT_TIMESTAMP,
		updated DATETIME DEFAULT CURRENT_TIMESTAMP
	);`
	_, err := db.Exec(query)
	if err != nil {
		fmt.Printf("Failed to create table: %v\n", err)
	}
}

// healthCheck handles GET /health
func healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, HealthResponse{Status: "ok"})
}

// listBooks handles GET /books with optional author filter
func listBooks(c *gin.Context) {
	author := c.Query("author")

	var books []Book
	var err error

	if author != "" {
		// Filter by author
		rows, err := db.Query("SELECT id, title, author, year, isbn, created, updated FROM books WHERE author = ?", author)
		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to query books"})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var book Book
			var created, updated string
			err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &created, &updated)
			if err != nil {
				c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to scan book"})
				return
			}
			book.Created, _ = time.Parse("2006-01-02 15:04:05", created)
			book.Updated, _ = time.Parse("2006-01-02 15:04:05", updated)
			books = append(books, book)
		}
	} else {
		// Get all books
		rows, err := db.Query("SELECT id, title, author, year, isbn, created, updated FROM books")
		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to query books"})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var book Book
			var created, updated string
			err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &created, &updated)
			if err != nil {
				c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to scan book"})
				return
			}
			book.Created, _ = time.Parse("2006-01-02 15:04:05", created)
			book.Updated, _ = time.Parse("2006-01-02 15:04:05", updated)
			books = append(books, book)
		}
	}

	if err == nil {
		c.JSON(http.StatusOK, books)
	} else {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: err.Error()})
	}
}

// createBook handles POST /books
func createBook(c *gin.Context) {
	var input BookInput

	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid input: " + err.Error()})
		return
	}

	// Validate title and author are not empty
	if strings.TrimSpace(input.Title) == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Title is required"})
		return
	}
	if strings.TrimSpace(input.Author) == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Author is required"})
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn, created, updated) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
		input.Title, input.Author, input.Year, input.ISBN,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to create book"})
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to get last insert ID"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"id":      id,
		"title":   input.Title,
		"author":  input.Author,
		"year":    input.Year,
		"isbn":    input.ISBN,
	})
}

// getBook handles GET /books/:id
func getBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid book ID"})
		return
	}

	var book Book
	var created, updated string
	err = db.QueryRow("SELECT id, title, author, year, isbn, created, updated FROM books WHERE id = ?", id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &created, &updated)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, ErrorResponse{Error: "Book not found"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to query book"})
		return
	}

	book.Created, _ = time.Parse("2006-01-02 15:04:05", created)
	book.Updated, _ = time.Parse("2006-01-02 15:04:05", updated)

	c.JSON(http.StatusOK, book)
}

// updateBook handles PUT /books/:id
func updateBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid book ID"})
		return
	}

	// Check if book exists
	var exists bool
	err = db.QueryRow("SELECT EXISTS(SELECT 1 FROM books WHERE id = ?)", id).Scan(&exists)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to check book existence"})
		return
	}
	if !exists {
		c.JSON(http.StatusNotFound, ErrorResponse{Error: "Book not found"})
		return
	}

	var input BookInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid input: " + err.Error()})
		return
	}

	// Validate title and author are not empty
	if strings.TrimSpace(input.Title) == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Title is required"})
		return
	}
	if strings.TrimSpace(input.Author) == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Author is required"})
		return
	}

	_, err = db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated = datetime('now') WHERE id = ?",
		input.Title, input.Author, input.Year, input.ISBN, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to update book"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"id":      id,
		"title":   input.Title,
		"author":  input.Author,
		"year":    input.Year,
		"isbn":    input.ISBN,
	})
}

// deleteBook handles DELETE /books/:id
func deleteBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid book ID"})
		return
	}

	// Check if book exists
	var exists bool
	err = db.QueryRow("SELECT EXISTS(SELECT 1 FROM books WHERE id = ?)", id).Scan(&exists)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to check book existence"})
		return
	}
	if !exists {
		c.JSON(http.StatusNotFound, ErrorResponse{Error: "Book not found"})
		return
	}

	_, err = db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to delete book"})
		return
	}

	c.JSON(http.StatusNoContent, nil)
}

// JSON response helper
func jsonResponse(c *gin.Context, status int, data interface{}) {
	c.JSON(status, data)
}
