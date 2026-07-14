package main

import (
	"database/sql"
	"log"
	"net/http"
	"strconv"

	_ "github.com/mattn/go-sqlite3"

	"github.com/gin-gonic/gin"
)

// Book represents a book entry.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// CreateBookRequest represents the request body for creating a book.
type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
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

// initDB opens (or creates) the SQLite database and ensures the books table exists.
func initDB() error {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		return err
	}

	createTable := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`

	_, err = db.Exec(createTable)
	if err != nil {
		return err
	}

	return nil
}

// validateBook checks that title and author are non-empty.
func validateBook(title, author string) (string, error) {
	if title == "" {
		return "title is required", nil
	}
	if author == "" {
		return "author is required", nil
	}
	return "", nil
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("failed to initialize database: %v", err)
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
		log.Fatalf("failed to start server: %v", err)
	}
}

// healthCheck returns a simple 200 OK response.
func healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// createBook handles POST /books.
func createBook(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	if msg, _ := validateBook(req.Title, req.Author); msg != "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": msg})
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
	book := Book{ID: int(id), Title: req.Title, Author: req.Author, Year: req.Year, ISBN: req.ISBN}

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
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query books"})
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to scan book"})
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
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN,
	)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query book"})
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
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	if msg, _ := validateBook(req.Title, req.Author); msg != "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": msg})
		return
	}

	result, err := db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		req.Title, req.Author, req.Year, req.ISBN, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update book"})
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "book updated successfully"})
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
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete book"})
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "book deleted successfully"})
}
