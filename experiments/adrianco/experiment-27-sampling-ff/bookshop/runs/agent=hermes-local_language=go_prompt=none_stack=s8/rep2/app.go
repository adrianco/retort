package main

import (
	"database/sql"
	"log"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book entry in the collection.
type Book struct {
	ID       int    `json:"id"`
	Title    string `json:"title"`
	Author   string `json:"author"`
	Year     int    `json:"year"`
	ISBN     string `json:"isbn"`
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

// initDB opens (or creates) the SQLite database and sets up the schema.
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
		year INTEGER,
		isbn TEXT
	);`

	if _, err = db.Exec(createTable); err != nil {
		return err
	}

	return nil
}

// scanRow maps a single database row into a Book.
func scanRow(rows *sql.Rows) (Book, error) {
	var b Book
	err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	r := gin.Default()

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	r.POST("/books", func(c *gin.Context) {
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
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		id, _ := result.LastInsertId()
		book := Book{ID: int(id), Title: req.Title, Author: req.Author, Year: req.Year, ISBN: req.ISBN}

		c.JSON(http.StatusCreated, book)
	})

	r.GET("/books", func(c *gin.Context) {
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
			b, err := scanRow(rows)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			books = append(books, b)
		}

		if books == nil {
			books = []Book{}
		}

		c.JSON(http.StatusOK, books)
	})

	r.GET("/books/:id", func(c *gin.Context) {
		id, err := strconv.Atoi(c.Param("id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
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
	})

	r.PUT("/books/:id", func(c *gin.Context) {
		id, err := strconv.Atoi(c.Param("id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
			return
		}

		var req UpdateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		result, err := db.Exec(
			"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
			req.Title, req.Author, req.Year, req.ISBN, id,
		)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		rowsAffected, _ := result.RowsAffected()
		if rowsAffected == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
			return
		}

		var b Book
		db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
			Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

		c.JSON(http.StatusOK, b)
	})

	r.DELETE("/books/:id", func(c *gin.Context) {
		id, err := strconv.Atoi(c.Param("id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
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
	})

	log.Println("Server starting on :8080")
	r.Run(":8080")
}
