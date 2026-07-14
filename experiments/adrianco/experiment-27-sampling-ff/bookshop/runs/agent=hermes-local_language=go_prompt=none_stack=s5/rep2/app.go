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
	ID       int    `json:"id"`
	Title    string `json:"title"`
	Author   string `json:"author"`
	Year     int    `json:"year"`
	ISBN     string `json:"isbn"`
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

func initDB() error {
	dbFile := "books.db"

	var err error
	db, err = sql.Open("sqlite3", dbFile)
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

	if _, err := db.Exec(createTableSQL); err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	return nil
}

func closeDB() {
	if db != nil {
		db.Close()
	}
}

func healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "ok",
		"message": "Service is healthy",
	})
}

func createBook(c *gin.Context) {
	var req CreateBookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body: title and author are required",
		})
		return
	}

	if req.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Title is required",
		})
		return
	}

	if req.Author == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Author is required",
		})
		return
	}

	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create book",
		})
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to get book ID",
		})
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

func listBooks(c *gin.Context) {
	authorFilter := c.Query("author")

	var books []Book

	if authorFilter != "" {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", authorFilter)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to query books",
			})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var book Book
			if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{
					"error": "Failed to scan book",
				})
				return
			}
			books = append(books, book)
		}
	} else {
		rows, err := db.Query("SELECT id, title, author, year, isbn FROM books")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to query books",
			})
			return
		}
		defer rows.Close()

		for rows.Next() {
			var book Book
			if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{
					"error": "Failed to scan book",
				})
				return
			}
			books = append(books, book)
		}
	}

	if books == nil {
		books = []Book{}
	}

	c.JSON(http.StatusOK, books)
}

func getBook(c *gin.Context) {
	idStr := c.Param("id")

	var id int
	if _, err := fmt.Sscanf(idStr, "%d", &id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid book ID",
		})
		return
	}

	var book Book
	err := db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN,
	)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Book not found",
		})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to query book",
		})
		return
	}

	c.JSON(http.StatusOK, book)
}

func updateBook(c *gin.Context) {
	idStr := c.Param("id")

	var id int
	if _, err := fmt.Sscanf(idStr, "%d", &id); err != nil {
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

	var existingBook Book
	err := db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(
		&existingBook.ID, &existingBook.Title, &existingBook.Author, &existingBook.Year, &existingBook.ISBN,
	)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Book not found",
		})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to query book",
		})
		return
	}

	title := existingBook.Title
	if req.Title != "" {
		title = req.Title
	}

	author := existingBook.Author
	if req.Author != "" {
		author = req.Author
	}

	year := existingBook.Year
	if req.Year != 0 {
		year = req.Year
	}

	isbn := existingBook.ISBN
	if req.ISBN != "" {
		isbn = req.ISBN
	}

	_, err = db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update book",
		})
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

func deleteBook(c *gin.Context) {
	idStr := c.Param("id")

	var id int
	if _, err := fmt.Sscanf(idStr, "%d", &id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid book ID",
		})
		return
	}

	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to delete book",
		})
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to verify deletion",
		})
		return
	}

	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Book not found",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Book deleted successfully",
	})
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer closeDB()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

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

	fmt.Printf("Server starting on port %s\n", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
