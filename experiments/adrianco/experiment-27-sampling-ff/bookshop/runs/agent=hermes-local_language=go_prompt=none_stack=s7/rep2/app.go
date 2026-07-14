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

// Database holds the SQLite connection
type Database struct {
	conn *sql.DB
}

// NewDatabase creates a new database connection
func NewDatabase(dbPath string) (*Database, error) {
	conn, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Enable WAL mode for better concurrent access
	_, err = conn.Exec("PRAGMA journal_mode=WAL")
	if err != nil {
		return nil, fmt.Errorf("failed to set journal mode: %w", err)
	}

	db := &Database{conn: conn}

	// Create books table if it doesn't exist
	err = db.CreateTable()
	if err != nil {
		return nil, fmt.Errorf("failed to create table: %w", err)
	}

	return db, nil
}

// CreateTable creates the books table
func (db *Database) CreateTable() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	_, err := db.conn.Exec(query)
	return err
}

// Close closes the database connection
func (db *Database) Close() error {
	return db.conn.Close()
}

// CreateBook inserts a new book and returns it with the generated ID
func (db *Database) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	result, err := db.conn.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		title, author, year, isbn,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("failed to get book ID: %w", err)
	}

	return &Book{
		ID:     int(id),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// GetAllBooks returns all books, optionally filtered by author
func (db *Database) GetAllBooks(authorFilter string) ([]Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		likeFilter := "%" + strings.ToLower(authorFilter) + "%"
		rows, err = db.conn.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?",
			likeFilter,
		)
	} else {
		rows, err = db.conn.Query(
			"SELECT id, title, author, year, isbn FROM books",
		)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to query books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
		if err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, b)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating books: %w", err)
	}

	return books, nil
}

// GetBook returns a single book by ID
func (db *Database) GetBook(id int) (*Book, error) {
	var b Book
	err := db.conn.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book not found with ID %d", id)
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}
	return &b, nil
}

// UpdateBook updates an existing book
func (db *Database) UpdateBook(id int, title, author string, year int, isbn string) (*Book, error) {
	// Check if book exists
	var exists int
	err := db.conn.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&exists)
	if err != nil {
		return nil, fmt.Errorf("failed to check book: %w", err)
	}
	if exists == 0 {
		return nil, fmt.Errorf("book not found with ID %d", id)
	}

	_, err = db.conn.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to update book: %w", err)
	}

	return &Book{
		ID:     id,
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// DeleteBook deletes a book by ID
func (db *Database) DeleteBook(id int) error {
	result, err := db.conn.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to check delete result: %w", err)
	}
	if rowsAffected == 0 {
		return fmt.Errorf("book not found with ID %d", id)
	}

	return nil
}

func main() {
	db, err := NewDatabase("books.db")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	router := gin.Default()

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "ok",
			"message": "Service is healthy",
		})
	})

	// Create a new book
	router.POST("/books", func(c *gin.Context) {
		var req CreateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request body. 'title' and 'author' are required fields.",
			})
			return
		}

		// Validate title is not empty
		req.Title = strings.TrimSpace(req.Title)
		if req.Title == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Title cannot be empty",
			})
			return
		}

		// Validate author is not empty
		req.Author = strings.TrimSpace(req.Author)
		if req.Author == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Author cannot be empty",
			})
			return
		}

		book, err := db.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": fmt.Sprintf("Failed to create book: %v", err),
			})
			return
		}

		c.JSON(http.StatusCreated, book)
	})

	// List all books with optional author filter
	router.GET("/books", func(c *gin.Context) {
		author := c.Query("author")

		books, err := db.GetAllBooks(author)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": fmt.Sprintf("Failed to retrieve books: %v", err),
			})
			return
		}

		if books == nil {
			books = []Book{}
		}

		c.JSON(http.StatusOK, gin.H{
			"books": books,
			"count": len(books),
		})
	})

	// Get a single book by ID
	router.GET("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		book, err := db.GetBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, book)
	})

	// Update a book
	router.PUT("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		var req UpdateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request body",
			})
			return
		}

		// Use existing values if not provided
		existingBook, err := db.GetBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": fmt.Sprintf("Book not found with ID %d", id),
			})
			return
		}

		title := req.Title
		if title == "" {
			title = existingBook.Title
		}
		author := req.Author
		if author == "" {
			author = existingBook.Author
		}
		year := req.Year
		if year == 0 {
			year = existingBook.Year
		}
		isbn := req.ISBN
		if isbn == "" {
			isbn = existingBook.ISBN
		}

		book, err := db.UpdateBook(id, title, author, year, isbn)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": fmt.Sprintf("Failed to update book: %v", err),
			})
			return
		}

		c.JSON(http.StatusOK, book)
	})

	// Delete a book
	router.DELETE("/books/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid book ID",
			})
			return
		}

		err = db.DeleteBook(id)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Book deleted successfully",
			"id":      id,
		})
	})

	fmt.Println("Server starting on http://localhost:8080")
	log.Fatal(router.Run(":8080"))
}
