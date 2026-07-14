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

// Book represents a book entity
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
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	return nil
}

// scanRow scans a database row into a Book
func scanRow(rows *sql.Rows) (Book, error) {
	var b Book
	err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

// openDB opens the database for testing (uses in-memory SQLite)
func openDB() (*sql.DB, error) {
	d, err := sql.Open("sqlite3", ":memory:?_busy_timeout=5000")
	if err != nil {
		return nil, err
	}

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`

	_, err = d.Exec(createTableSQL)
	if err != nil {
		d.Close()
		return nil, err
	}

	return d, nil
}

// healthHandler handles GET /health
func healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// createBookHandler handles POST /books
func createBookHandler(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	// Validate required fields
	req.Title = strings.TrimSpace(req.Title)
	req.Author = strings.TrimSpace(req.Author)

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
		"id":     int(id),
		"title":  req.Title,
		"author": req.Author,
		"year":   req.Year,
		"isbn":   req.ISBN,
	})
}

// listBooksHandler handles GET /books
func listBooksHandler(c *gin.Context) {
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

	books := []Book{}
	for rows.Next() {
		b, err := scanRow(rows)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to scan book"})
			return
		}
		books = append(books, b)
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
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid book ID"})
		return
	}

	var b Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN,
	)
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

// updateBookHandler handles PUT /books/:id
func updateBookHandler(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid book ID"})
		return
	}

	// Check if book exists
	var existingBook Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN,
	)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query book"})
		return
	}

	var req UpdateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	title := existingBook.Title
	author := existingBook.Author
	year := existingBook.Year
	isbn := existingBook.ISBN

	if req.Title != nil {
		trimmed := strings.TrimSpace(*req.Title)
		if trimmed == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Title cannot be empty"})
			return
		}
		title = trimmed
	}
	if req.Author != nil {
		trimmed := strings.TrimSpace(*req.Author)
		if trimmed == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Author cannot be empty"})
			return
		}
		author = trimmed
	}
	if req.Year != nil {
		year = *req.Year
	}
	if req.ISBN != nil {
		isbn = *req.ISBN
	}

	_, err = db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update book"})
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

// deleteBookHandler handles DELETE /books/:id
func deleteBookHandler(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid book ID"})
		return
	}

	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete book"})
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to check deletion result"})
		return
	}

	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "Book not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Book deleted successfully"})
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	r := gin.Default()

	r.GET("/health", healthHandler)
	r.POST("/books", createBookHandler)
	r.GET("/books", listBooksHandler)
	r.GET("/books/:id", getBookHandler)
	r.PUT("/books/:id", updateBookHandler)
	r.DELETE("/books/:id", deleteBookHandler)

	fmt.Println("Server starting on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
