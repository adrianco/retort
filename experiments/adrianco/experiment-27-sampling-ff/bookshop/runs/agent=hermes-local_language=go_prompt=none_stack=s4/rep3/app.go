package main

import (
	"database/sql"
	"log"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book entity.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// CreateBookRequest represents the request body for creating a book.
type CreateBookRequest struct {
	Title  string `json:"title" binding:"required"`
	Author string `json:"author" binding:"required"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// UpdateBookRequest represents the request body for updating a book.
type UpdateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var db *sql.DB

// initDB opens (or creates) the SQLite database and creates the books table.
func initDB() error {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		return err
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = db.Exec(createTable)
	if err != nil {
		return err
	}

	return nil
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	r := gin.Default()

	r.GET("/health", healthCheck)
	r.POST("/books", createBook)
	r.GET("/books", listBooks)
	r.GET("/books/:id", getBook)
	r.PUT("/books/:id", updateBook)
	r.DELETE("/books/:id", deleteBook)

	log.Println("Server starting on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

// healthCheck returns a simple health status.
func healthCheck(c *gin.Context) {
	if err := db.Ping(); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "database unavailable"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// createBook handles POST /books.
func createBook(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "title is required"})
		return
	}
	if req.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "author is required"})
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
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

// listBooks handles GET /books with optional ?author= filter.
func listBooks(c *gin.Context) {
	author := c.Query("author")

	var rows *sql.Rows
	var err error

	if author != "" {
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
	} else {
		rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		books = append(books, b)
	}

	if books == nil {
		books = []Book{}
	}

	c.JSON(http.StatusOK, books)
}

// getBook handles GET /books/:id.
func getBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	var b Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, b)
}

// updateBook handles PUT /books/:id.
func updateBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	var req UpdateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Check if book exists
	var existing Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&existing.ID, &existing.Title, &existing.Author, &existing.Year, &existing.ISBN)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
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
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"id":     id,
		"title":  title,
		"author": author,
		"year":   year,
		"isbn":   isbn,
	})
}

// deleteBook handles DELETE /books/:id.
func deleteBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "book deleted"})
}
