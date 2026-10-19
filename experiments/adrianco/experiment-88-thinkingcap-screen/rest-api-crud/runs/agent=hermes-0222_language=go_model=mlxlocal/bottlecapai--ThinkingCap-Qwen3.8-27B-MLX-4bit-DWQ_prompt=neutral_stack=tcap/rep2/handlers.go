package main

import (
	"errors"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

// API holds the HTTP handlers for the book service.
type API struct {
	store *Store
}

// NewRouter wires all routes onto a fresh gin engine.
func NewRouter(store *Store) *gin.Engine {
	r := gin.New()
	r.Use(gin.Recovery())

	api := &API{store: store}
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "book-api",
			"endpoints": []string{"GET /health", "POST /books", "GET /books", "GET /books/{id}", "PUT /books/{id}", "DELETE /books/{id}"},
		})
	})
	r.GET("/health", api.Health)
	r.POST("/books", api.CreateBook)
	r.GET("/books", api.ListBooks)
	r.GET("/books/:id", api.GetBook)
	r.PUT("/books/:id", api.UpdateBook)
	r.DELETE("/books/:id", api.DeleteBook)

	r.NoRoute(func(c *gin.Context) {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
	})
	return r
}

// Health reports service status and verifies DB connectivity.
func (a *API) Health(c *gin.Context) {
	if err := a.store.Ping(); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"status": "unhealthy", "error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// CreateBook handles POST /books.
func (a *API) CreateBook(c *gin.Context) {
	var b Book
	if err := c.ShouldBindJSON(&b); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid JSON body: " + err.Error()})
		return
	}
	normalize(&b)
	if err := validateBook(&b); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := a.store.Create(&b); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create book"})
		return
	}
	c.JSON(http.StatusCreated, b)
}

// ListBooks handles GET /books, with an optional ?author= filter.
func (a *API) ListBooks(c *gin.Context) {
	books, err := a.store.List(c.Query("author"))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list books"})
		return
	}
	c.JSON(http.StatusOK, books)
}

// GetBook handles GET /books/{id}.
func (a *API) GetBook(c *gin.Context) {
	id, ok := parseIDParam(c)
	if !ok {
		return
	}
	b, err := a.store.Get(id)
	if errors.Is(err, ErrNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get book"})
		return
	}
	c.JSON(http.StatusOK, b)
}

// UpdateBook handles PUT /books/{id}.
func (a *API) UpdateBook(c *gin.Context) {
	id, ok := parseIDParam(c)
	if !ok {
		return
	}
	var b Book
	if err := c.ShouldBindJSON(&b); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid JSON body: " + err.Error()})
		return
	}
	b.ID = id
	normalize(&b)
	if err := validateBook(&b); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := a.store.Update(&b); err != nil {
		if errors.Is(err, ErrNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update book"})
		return
	}
	c.JSON(http.StatusOK, b)
}

// DeleteBook handles DELETE /books/{id}.
func (a *API) DeleteBook(c *gin.Context) {
	id, ok := parseIDParam(c)
	if !ok {
		return
	}
	if err := a.store.Delete(id); err != nil {
		if errors.Is(err, ErrNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete book"})
		return
	}
	c.Status(http.StatusNoContent)
}

// parseIDParam parses the :id path parameter, writing a 400 response
// and returning ok=false on failure.
func parseIDParam(c *gin.Context) (int64, bool) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid book id"})
		return 0, false
	}
	return id, true
}

// normalize trims surrounding whitespace from string fields.
func normalize(b *Book) {
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
}

// validateBook enforces the input rules: title and author are required,
// year must be non-negative.
func validateBook(b *Book) error {
	if b.Title == "" {
		return errors.New("title is required")
	}
	if b.Author == "" {
		return errors.New("author is required")
	}
	if b.Year < 0 {
		return errors.New("year must be a non-negative integer")
	}
	return nil
}
