package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in the collection.
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
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

var db *sql.DB

// initDB initializes the SQLite database and creates the books table if it doesn't exist.
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
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	return nil
}

// scanBook scans a database row into a Book struct.
func scanBook(row *sql.Row) (*Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		return nil, fmt.Errorf("failed to scan book: %w", err)
	}
	return &b, nil
}

// validateBook validates the required fields for a book.
func validateBook(title, author string) (string, int) {
	if title == "" && author == "" {
		return "title and author are required", http.StatusBadRequest
	}
	if title == "" {
		return "title is required", http.StatusBadRequest
	}
	if author == "" {
		return "author is required", http.StatusBadRequest
	}
	return "", 0
}

// healthCheck handles the GET /health endpoint.
func healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
	})
}

// createBook handles the POST /books endpoint.
func createBook(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	if errText, statusCode := validateBook(req.Title, req.Author); errText != "" {
		c.JSON(statusCode, gin.H{"error": errText})
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

	id, err := result.LastInsertId()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get book ID"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"id":     int(id),
		"title":  req.Title,
		"author": req.Author,
		"year":   req.Year,
		"isbn":   req.ISBN,
	})
}

// listBooks handles the GET /books endpoint.
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

// getBook handles the GET /books/:id endpoint.
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

// updateBook handles the PUT /books/:id endpoint.
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

	var existingBook Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN,
	)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query book"})
		return
	}

	title := req.Title
	if title == nil {
		t := existingBook.Title
		title = &t
	}

	author := req.Author
	if author == nil {
		a := existingBook.Author
		author = &a
	}

	year := req.Year
	if year == nil {
		y := existingBook.Year
		year = &y
	}

	isbn := req.ISBN
	if isbn == nil {
		i := existingBook.ISBN
		isbn = &i
	}

	if errText, statusCode := validateBook(*title, *author); errText != "" {
		c.JSON(statusCode, gin.H{"error": errText})
		return
	}

	_, err = db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		*title, *author, *year, *isbn, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update book"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"id":     id,
		"title":  *title,
		"author": *author,
		"year":   *year,
		"isbn":   *isbn,
	})
}

// deleteBook handles the DELETE /books/:id endpoint.
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

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to check deletion"})
		return
	}

	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "book deleted successfully"})
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	r := gin.Default()

	r.GET("/health", healthCheck)

	books := r.Group("/books")
	{
		books.POST("", createBook)
		books.GET("", listBooks)
		books.GET("/:id", getBook)
		books.PUT("/:id", updateBook)
		books.DELETE("/:id", deleteBook)
	}

	r.Run(":8080")
	fmt.Println("Server started on http://localhost:8080")
}
