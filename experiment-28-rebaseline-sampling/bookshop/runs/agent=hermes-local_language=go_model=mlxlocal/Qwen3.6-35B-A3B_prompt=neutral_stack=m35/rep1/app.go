package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

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
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

var db *sql.DB

// initDB opens (or creates) the SQLite database and creates the books table if it doesn't exist
func initDB() error {
	var err error
	db, err = sql.Open("sqlite3", "./books.db?_busy_timeout=5000")
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`

	_, err = db.Exec(createTable)
	if err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	return nil
}

// validateBook validates required fields
func validateBook(title, author string) (string, int) {
	title = strings.TrimSpace(title)
	author = strings.TrimSpace(author)
	if title == "" {
		return "title is required", http.StatusBadRequest
	}
	if author == "" {
		return "author is required", http.StatusBadRequest
	}
	return "", 0
}

// healthHandler returns a simple health check response
func healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// createBookHandler handles POST /books
func createBookHandler(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid JSON body"})
		return
	}

	if errMsg, status := validateBook(req.Title, req.Author); errMsg != "" {
		c.JSON(status, gin.H{"error": errMsg})
		return
	}

	year := req.Year
	if year == 0 {
		year = 2000 // default year
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, year, req.ISBN,
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
		Year:   year,
		ISBN:   req.ISBN,
	}

	c.JSON(http.StatusCreated, book)
}

// listBooksHandler handles GET /books
func listBooksHandler(c *gin.Context) {
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
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to scan row"})
			return
		}
		books = append(books, b)
	}

	if err := rows.Err(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "row iteration error"})
		return
	}

	if books == nil {
		books = []Book{}
	}

	c.JSON(http.StatusOK, books)
}

// getBookHandler handles GET /books/:id
func getBookHandler(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	var book Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)

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
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
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
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query book"})
		return
	}

	var req UpdateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid JSON body"})
		return
	}

	title := existing.Title
	author := existing.Author
	year := existing.Year
	isbn := existing.ISBN

	if req.Title != nil {
		title = *req.Title
	}
	if req.Author != nil {
		author = *req.Author
	}
	if req.Year != nil {
		year = *req.Year
	}
	if req.ISBN != nil {
		isbn = *req.ISBN
	}

	if errMsg, status := validateBook(title, author); errMsg != "" {
		c.JSON(status, gin.H{"error": errMsg})
		return
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
		ID:     id,
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}

	c.JSON(http.StatusOK, book)
}

// deleteBookHandler handles DELETE /books/:id
func deleteBookHandler(c *gin.Context) {
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

	c.JSON(http.StatusOK, gin.H{"message": "book deleted"})
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	// Ensure we use the release mode in production
	gin.SetMode(gin.ReleaseMode)

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

	fmt.Println("Server starting on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
