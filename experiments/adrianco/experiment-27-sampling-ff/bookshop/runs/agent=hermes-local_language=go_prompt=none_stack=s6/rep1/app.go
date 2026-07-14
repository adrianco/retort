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

	// Enable foreign keys
	if _, err := conn.Exec("PRAGMA foreign_keys = ON"); err != nil {
		return nil, fmt.Errorf("failed to enable foreign keys: %w", err)
	}

	// Create books table if it doesn't exist
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	if _, err := conn.Exec(createTableSQL); err != nil {
		return nil, fmt.Errorf("failed to create table: %w", err)
	}

	return &Database{conn: conn}, nil
}

// Close closes the database connection
func (db *Database) Close() error {
	return db.conn.Close()
}

// CreateBook creates a new book in the database
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
		return nil, fmt.Errorf("failed to get last insert id: %w", err)
	}

	return &Book{
		ID:     int(id),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// GetBook retrieves a single book by ID
func (db *Database) GetBook(id int) (*Book, error) {
	var book Book
	err := db.conn.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book with ID %d not found", id)
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}
	return &book, nil
}

// ListBooks retrieves all books, optionally filtered by author
func (db *Database) ListBooks(authorFilter string) ([]Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		rows, err = db.conn.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?",
			"%"+authorFilter+"%",
		)
	} else {
		rows, err = db.conn.Query(
			"SELECT id, title, author, year, isbn FROM books",
		)
	}
	if err != nil {
		return nil, fmt.Errorf("failed to list books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, book)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating books: %w", err)
	}

	return books, nil
}

// UpdateBook updates an existing book
func (db *Database) UpdateBook(id int, title, author string, year int, isbn string) (*Book, error) {
	// Check if the book exists
	var exists int
	err := db.conn.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&exists)
	if err != nil {
		return nil, fmt.Errorf("failed to check book existence: %w", err)
	}
	if exists == 0 {
		return nil, fmt.Errorf("book with ID %d not found", id)
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
		return fmt.Errorf("failed to get rows affected: %w", err)
	}

	if rowsAffected == 0 {
		return fmt.Errorf("book with ID %d not found", id)
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

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"message": "Book API is running",
		})
	})

	// Create a new book
	router.POST("/books", func(c *gin.Context) {
		var req CreateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request body: " + err.Error(),
			})
			return
		}

		// Validate title and author are not empty
		if strings.TrimSpace(req.Title) == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Title is required and cannot be empty",
			})
			return
		}
		if strings.TrimSpace(req.Author) == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Author is required and cannot be empty",
			})
			return
		}

		book, err := db.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusCreated, book)
	})

	// List all books
	router.GET("/books", func(c *gin.Context) {
		author := c.Query("author")

		books, err := db.ListBooks(author)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
			})
			return
		}

		if books == nil {
			books = []Book{}
		}

		c.JSON(http.StatusOK, books)
	})

	// Get a single book
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
			if strings.Contains(err.Error(), "not found") {
				c.JSON(http.StatusNotFound, gin.H{
					"error": err.Error(),
				})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{
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
				"error": "Invalid request body: " + err.Error(),
			})
			return
		}

		// Validate title and author if provided
		if req.Title != "" && strings.TrimSpace(req.Title) == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Title cannot be empty",
			})
			return
		}
		if req.Author != "" && strings.TrimSpace(req.Author) == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Author cannot be empty",
			})
			return
		}

		book, err := db.UpdateBook(id, req.Title, req.Author, req.Year, req.ISBN)
		if err != nil {
			if strings.Contains(err.Error(), "not found") {
				c.JSON(http.StatusNotFound, gin.H{
					"error": err.Error(),
				})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
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
			if strings.Contains(err.Error(), "not found") {
				c.JSON(http.StatusNotFound, gin.H{
					"error": err.Error(),
				})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Book deleted successfully",
		})
	})

	log.Println("Starting Book API server on :8080")
	if err := router.Run(":8080"); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
