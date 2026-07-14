package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCreateBook(t *testing.T) {
	// Create a test database
	db, err := initDB()
	assert.NoError(t, err)
	defer db.Close()

	service := NewBookService(db)

	// Create a book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	// Convert to JSON
	jsonData, _ := json.Marshal(book)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	// Create a response recorder
	rr := httptest.NewRecorder()

	// Call the handler
	service.CreateBook(rr, req)

	// Check the status code
	assert.Equal(t, http.StatusCreated, rr.Code)

	// Check the response body
	var responseBook Book
	err = json.Unmarshal(rr.Body.Bytes(), &responseBook)
	assert.NoError(t, err)
	assert.Equal(t, book.Title, responseBook.Title)
	assert.Equal(t, book.Author, responseBook.Author)
	assert.Equal(t, book.Year, responseBook.Year)
	assert.Equal(t, book.ISBN, responseBook.ISBN)
}

func TestGetBook(t *testing.T) {
	// Create a test database
	db, err := initDB()
	assert.NoError(t, err)
	defer db.Close()

	service := NewBookService(db)

	// First create a book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	// Insert book into database
	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
	assert.NoError(t, err)

	// Get the inserted ID
	id, err := result.LastInsertId()
	assert.NoError(t, err)

	// Create a GET request
	req := httptest.NewRequest("GET", "/books/"+strconv.FormatInt(id, 10), nil)

	// Create a response recorder
	rr := httptest.NewRecorder()

	// Call the handler
	service.GetBook(rr, req)

	// Check the status code
	assert.Equal(t, http.StatusOK, rr.Code)

	// Check the response body
	var responseBook Book
	err = json.Unmarshal(rr.Body.Bytes(), &responseBook)
	assert.NoError(t, err)
	assert.Equal(t, book.Title, responseBook.Title)
	assert.Equal(t, book.Author, responseBook.Author)
	assert.Equal(t, book.Year, responseBook.Year)
	assert.Equal(t, book.ISBN, responseBook.ISBN)
}

func TestListBooks(t *testing.T) {
	// Create a test database
	db, err := initDB()
	assert.NoError(t, err)
	defer db.Close()

	service := NewBookService(db)

	// Create a book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "1234567890",
	}

	// Insert book into database
	_, err = db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
	assert.NoError(t, err)

	// Create a GET request
	req := httptest.NewRequest("GET", "/books", nil)

	// Create a response recorder
	rr := httptest.NewRecorder()

	// Call the handler
	service.ListBooks(rr, req)

	// Check the status code
	assert.Equal(t, http.StatusOK, rr.Code)

	// Check the response body
	var books []Book
	err = json.Unmarshal(rr.Body.Bytes(), &books)
	assert.NoError(t, err)
	assert.Len(t, books, 1)
	assert.Equal(t, book.Title, books[0].Title)
	assert.Equal(t, book.Author, books[0].Author)
	assert.Equal(t, book.Year, books[0].Year)
	assert.Equal(t, book.ISBN, books[0].ISBN)
}
