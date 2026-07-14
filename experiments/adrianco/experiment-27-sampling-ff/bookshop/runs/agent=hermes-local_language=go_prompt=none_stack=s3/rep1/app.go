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
	Title  string `json:"title" binding:"required"`
	Author string `json:"author" binding:"required"`
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
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	return nil
}

// healthHandler handles GET /health
func healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "healthy",
	})
}

// createBookHandler handles POST /books
func createBookHandler(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create book"})
		return
	}

	id, _ := result.LastInsertId()
	book := Book{
		ID:     int(id),
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	c.JSON(http.StatusCreated, book)
}

// listBooksHandler handles GET /books with optional ?author= filter
func listBooksHandler(c *gin.Context) {
	author := c.Query("author")

	var books []Book

	if author != "" {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query books"})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var b Book
			if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to scan book"})
				return
			}
			books = append(books, b)
		}
	} else {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query books"})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var b Book
			if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to scan book"})
				return
			}
			books = append(books, b)
		}
	}

	if books == nil {
		books = []Book{}
	}

	c.JSON(http.StatusOK, books)
}

// getBookHandler handles GET /books/:id
func getBookHandler(c *gin.Context) {
	id := c.Param("id")

	var book Book
	err := db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query book"})
		return
	}

	c.JSON(http.StatusOK, book)
}

// updateBookHandler handles PUT /books/:id
func updateBookHandler(c *gin.Context) {
	id := c.Param("id")

	var req UpdateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Check if book exists
	var existing Book
	err := db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&existing.ID, &existing.Title, &existing.Author, &existing.Year, &existing.ISBN)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query book"})
		return
	}

	title := existing.Title
	author := existing.Author
	year := existing.Year
	isbn := existing.ISBN

	if req.Title != "" {
		title = req.Title
	}
	if req.Author != "" {
		author = req.Author
	}
	if req.Year != 0 {
		year = req.Year
	}
	if req.ISBN != "" {
		isbn = req.ISBN
	}

	_, err = db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update book"})
		return
	}

	book := Book{
		ID:     existing.ID,
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}

	c.JSON(http.StatusOK, book)
}

// deleteBookHandler handles DELETE /books/:id
func deleteBookHandler(c *gin.Context) {
	id := c.Param("id")

	// Check if book exists
	var existing Book
	err := db.QueryRow(
		"SELECT id FROM books WHERE id = ?", id,
	).Scan(&existing.ID)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query book"})
		return
	}

	_, err = db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete book"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "book deleted"})
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	r := gin.Default()

	r.GET("/health", healthHandler)

	books := r.Group("/books")
	{
		books.POST("", createBookHandler)
		books.GET("", listBooksHandler)
		books.GET("/:id", getBookHandler)
		books.PUT("/:id", updateBookHandler)
		books.DELETE("/:id", deleteBookHandler)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Starting server on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
