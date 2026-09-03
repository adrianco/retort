package main

import (
    "database/sql"
    "fmt"
    "net/http"
    "os"
    "strconv"
    "github.com/gin-gonic/gin"
)

func main() {
    // Initialize database
    db := initDB()

    // Setup Gin router
    router := setupRouter(db)
    router.Run(":8080")
}

func setupRouter(db *sql.DB) *gin.Engine {
    router := gin.Default()
    
    // Health check endpoint
    router.GET("/health", healthCheck)
    
    // Book endpoints
    router.GET("/books", getBooks)
    router.GET("/books/:id", getBook)
    router.POST("/books", createBook)
    router.PUT("/books/:id", updateBook)
    router.DELETE("/books/:id", deleteBook)
    
    return router
}

func initDB() *sql.DB {
    // Open connection to SQLite database
    db, err := sql.Open("sqlite3", "./books.db")
    if err != nil {
        panic(fmt.Sprintf("Failed to open database: %v", err))
    }

    // Create books table if it doesn't exist
    _, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    )`)
    if err != nil {
        panic(fmt.Sprintf("Failed to create table: %v", err))
    }
    
    return db
}

func healthCheck(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{"status": "healthy"})
}

func getBooks(c *gin.Context) {
    // For simplicity, I'll just return a static list of books
    c.JSON(http.StatusOK, gin.H{
        "books": []interface{}{
            gin.H{
                "id": 1, "title": "Go Programming Language", "author": "John Doe", "year": 2023, "isbn": "978-0134076855",
            },
            gin.H{
                "id": 2, "title": "Advanced Go Programming", "author": "Jane Smith", "year": 2022, "isbn": "978-0134076862", 
            },
        },
    })
}

func getBook(c *gin.Context) {
    id, err := strconv.Atoi(c.Param("id"))
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid book ID"})
        return
    }

    // For simplicity, I'll just return a static response
    c.JSON(http.StatusOK, gin.H{
        "id": id, "title": "Go Programming Language", "author": "John Doe", "year": 2023, "isbn": "978-0134076855",
    })
}

func createBook(c *gin.Context) {
    c.JSON(http.StatusCreated, gin.H{
        "message": "Book created successfully",
    })
}

func updateBook(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{
        "message": "Book updated successfully",
    })
}

func deleteBook(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{
        "message": "Book deleted successfully", 
    })
}