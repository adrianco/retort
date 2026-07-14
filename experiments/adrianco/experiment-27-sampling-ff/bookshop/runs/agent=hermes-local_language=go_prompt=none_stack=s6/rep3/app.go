package main

import (
	"database/sql"
	"log"
	"net/http"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
	"github.com/gin-gonic/gin"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}

var db *sql.DB

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

func healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func createBook(c *gin.Context) {
	var input BookInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid JSON"})
		return
	}

	if input.Title == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Title is required"})
		return
	}
	if input.Author == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Author is required"})
		return
	}

	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		input.Title, input.Author, input.Year, input.ISBN)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to create book"})
		return
	}

	id, _ := result.LastInsertId()
	book := Book{
		ID:     int(id),
		Title:  input.Title,
		Author: input.Author,
		Year:   input.Year,
		ISBN:   input.ISBN,
	}

	c.JSON(http.StatusCreated, book)
}

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
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to query books"})
		return
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to scan book"})
			return
		}
		books = append(books, b)
	}

	if books == nil {
		books = []Book{}
	}

	c.JSON(http.StatusOK, books)
}

func getBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid book ID"})
		return
	}

	var book Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, ErrorResponse{Error: "Book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to query book"})
		return
	}

	c.JSON(http.StatusOK, book)
}

func updateBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid book ID"})
		return
	}

	var input BookInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid JSON"})
		return
	}

	if input.Title == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Title is required"})
		return
	}
	if input.Author == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Author is required"})
		return
	}

	result, err := db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		input.Title, input.Author, input.Year, input.ISBN, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to update book"})
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, ErrorResponse{Error: "Book not found"})
		return
	}

	book := Book{
		ID:     id,
		Title:  input.Title,
		Author: input.Author,
		Year:   input.Year,
		ISBN:   input.ISBN,
	}

	c.JSON(http.StatusOK, book)
}

func deleteBook(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Error: "Invalid book ID"})
		return
	}

	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "Failed to delete book"})
		return
	}

	rowsAffected, _ := result.RowsAffected()
	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, ErrorResponse{Error: "Book not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Book deleted"})
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	r := gin.Default()

	r.GET("/health", healthHandler)

	r.POST("/books", createBook)
	r.GET("/books", listBooks)
	r.GET("/books/:id", getBook)
	r.PUT("/books/:id", updateBook)
	r.DELETE("/books/:id", deleteBook)

	log.Println("Server starting on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
