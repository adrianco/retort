package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	sqliteDriver "modernc.org/sqlite"
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

// Database holds the SQLite connection
type Database struct {
	conn *sql.DB
}

// NewDatabase creates a new in-memory SQLite database and initializes the schema
func NewDatabase() (*Database, error) {
	drv, err := sqliteDriver.Driver(sqliteDriver.Config{})
	if err != nil {
		return nil, fmt.Errorf("failed to create sqlite driver: %w", err)
	}

	conn, err := sql.Open(drv, ":memory:")
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	db := &Database{conn: conn}
	if err := db.initSchema(); err != nil {
		return nil, fmt.Errorf("failed to initialize schema: %w", err)
	}

	return db, nil
}

// initSchema creates the books table if it doesn't exist
func (db *Database) initSchema() error {
	query := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`
	_, err := db.conn.Exec(query)
	return err
}

// Close closes the database connection
func (db *Database) Close() error {
	return db.conn.Close()
}

// bookAPI provides HTTP handlers for the book API
type bookAPI struct {
	db *Database
}

// newBookAPI creates a new bookAPI instance
func newBookAPI(db *Database) *bookAPI {
	return &bookAPI{db: db}
}

// getBooksHandler handles GET /books (list all books, with optional ?author= filter)
func (api *bookAPI) getBooksHandler(c *gin.Context) {
	author := c.Query("author")

	var rows *sql.Rows
	var err error

	if author != "" {
		rows, err = api.db.conn.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author = ?",
			author,
		)
	} else {
		rows, err = api.db.conn.Query("SELECT id, title, author, year, isbn FROM books")
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
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to scan book row"})
			return
		}
		books = append(books, b)
	}

	if err := rows.Err(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "error iterating book rows"})
		return
	}

	if books == nil {
		books = []Book{}
	}

	c.JSON(http.StatusOK, books)
}

// createBookHandler handles POST /books (create a new book)
func (api *bookAPI) createBookHandler(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	if err := validateCreateBook(req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := api.db.conn.Exec(
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

	book := Book{
		ID:     int(id),
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	c.JSON(http.StatusCreated, book)
}

// getBookHandler handles GET /books/:id (get a single book by ID)
func (api *bookAPI) getBookHandler(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	var b Book
	err = api.db.conn.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

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

// updateBookHandler handles PUT /books/:id (update a book)
func (api *bookAPI) updateBookHandler(c *gin.Context) {
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

	// Check if book exists
	var existingBook Book
	err = api.db.conn.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query book"})
		return
	}

	title := existingBook.Title
	if req.Title != nil {
		title = *req.Title
	}

	author := existingBook.Author
	if req.Author != nil {
		author = *req.Author
	}

	year := existingBook.Year
	if req.Year != nil {
		year = *req.Year
	}

	isbn := existingBook.ISBN
	if req.ISBN != nil {
		isbn = *req.ISBN
	}

	if err := validateUpdateBook(title, author); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	_, err = api.db.conn.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update book"})
		return
	}

	updatedBook := Book{
		ID:     id,
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}

	c.JSON(http.StatusOK, updatedBook)
}

// deleteBookHandler handles DELETE /books/:id (delete a book)
func (api *bookAPI) deleteBookHandler(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book ID"})
		return
	}

	result, err := api.db.conn.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete book"})
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to check delete result"})
		return
	}

	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "book deleted"})
}

// healthCheckHandler handles GET /health (health check endpoint)
func healthCheckHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// validateCreateBook validates the required fields for creating a book
func validateCreateBook(req CreateBookRequest) error {
	if strings.TrimSpace(req.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(req.Author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

// validateUpdateBook validates the required fields for updating a book
func validateUpdateBook(title, author string) error {
	if strings.TrimSpace(title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

func main() {
	db, err := NewDatabase()
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	api := newBookAPI(db)

	router := gin.Default()

	// Health check
	router.GET("/health", healthCheckHandler)

	// Book routes
	router.GET("/books", api.getBooksHandler)
	router.POST("/books", api.createBookHandler)
	router.GET("/books/:id", api.getBookHandler)
	router.PUT("/books/:id", api.updateBookHandler)
	router.DELETE("/books/:id", api.deleteBookHandler)

	log.Println("Starting server on :8080")
	if err := router.Run(":8080"); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
