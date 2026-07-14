package handler

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"book-api/internal/model"
	"github.com/gorilla/mux"
	_ "github.com/mattn/go-sqlite3"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHealthCheck(t *testing.T) {
	bookStore := model.NewBookStore(nil)
	handler := NewBookHandler(bookStore)

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	handler.HealthCheck(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "application/json", w.Header().Get("Content-Type"))

	var resp map[string]string
	err := json.NewDecoder(w.Body).Decode(&resp)
	require.NoError(t, err)
	assert.Equal(t, "healthy", resp["status"])
}

func TestCreateBook(t *testing.T) {
	db, err := sql.Open("sqlite3", ":memory:")
	require.NoError(t, err)
	defer db.Close()

	// Create table for in-memory test
	_, err = db.Exec(`
		CREATE TABLE books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL,
			isbn TEXT NOT NULL,
			created_at DATETIME NOT NULL,
			updated_at DATETIME NOT NULL
		)
	`)
	require.NoError(t, err)

	bookStore := model.NewBookStore(db)
	handler := NewBookHandler(bookStore)

	reqBody := BookRequest{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2024,
		ISBN:   "1234567890",
	}
	body, _ := json.Marshal(reqBody)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	w := httptest.NewRecorder()
	handler.CreateBook(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	assert.Equal(t, "application/json", w.Header().Get("Content-Type"))

	var resp model.Book
	err = json.NewDecoder(w.Body).Decode(&resp)
	require.NoError(t, err)
	assert.Equal(t, "Test Book", resp.Title)
	assert.Equal(t, "Test Author", resp.Author)
	assert.Equal(t, 2024, resp.Year)
	assert.Equal(t, "1234567890", resp.ISBN)
}

func TestCreateBookValidationError(t *testing.T) {
	bookStore := model.NewBookStore(nil)
	handler := NewBookHandler(bookStore)

	t.Run("missing title", func(t *testing.T) {
		reqBody := BookRequest{
			Author: "Test Author",
			Year:   2024,
			ISBN:   "1234567890",
		}
		body, _ := json.Marshal(reqBody)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		w := httptest.NewRecorder()
		handler.CreateBook(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})

	t.Run("missing author", func(t *testing.T) {
		reqBody := BookRequest{
			Title: "Test Book",
			Year:  2024,
			ISBN:  "1234567890",
		}
		body, _ := json.Marshal(reqBody)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		w := httptest.NewRecorder()
		handler.CreateBook(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})

	t.Run("invalid JSON", func(t *testing.T) {
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer([]byte("invalid json")))
		w := httptest.NewRecorder()
		handler.CreateBook(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})
}

func TestGetBook(t *testing.T) {
	db, err := sql.Open("sqlite3", ":memory:")
	require.NoError(t, err)
	defer db.Close()

	// Create table and insert test data
	_, err = db.Exec(`
		CREATE TABLE books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL,
			isbn TEXT NOT NULL,
			created_at DATETIME NOT NULL,
			updated_at DATETIME NOT NULL
		)
	`)
	require.NoError(t, err)

	_, err = db.Exec("INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
		"Test Book", "Test Author", 2024, "1234567890", "2024-01-01", "2024-01-01")
	require.NoError(t, err)

	bookStore := model.NewBookStore(db)
	handler := NewBookHandler(bookStore)

	req := httptest.NewRequest("GET", "/books/1", nil)
	w := httptest.NewRecorder()
	req = mux.SetURLVars(req, map[string]string{"id": "1"})
	handler.GetBook(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var resp model.Book
	err = json.NewDecoder(w.Body).Decode(&resp)
	require.NoError(t, err)
	assert.Equal(t, "Test Book", resp.Title)
}

func TestGetBookNotFound(t *testing.T) {
	db, err := sql.Open("sqlite3", ":memory:")
	require.NoError(t, err)
	defer db.Close()

	// Create table only (no data)
	_, err = db.Exec(`
		CREATE TABLE books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL,
			isbn TEXT NOT NULL,
			created_at DATETIME NOT NULL,
			updated_at DATETIME NOT NULL
		)
	`)
	require.NoError(t, err)

	bookStore := model.NewBookStore(db)
	handler := NewBookHandler(bookStore)

	req := httptest.NewRequest("GET", "/books/999", nil)
	w := httptest.NewRecorder()
	req = mux.SetURLVars(req, map[string]string{"id": "999"})
	handler.GetBook(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestDeleteBook(t *testing.T) {
	db, err := sql.Open("sqlite3", ":memory:")
	require.NoError(t, err)
	defer db.Close()

	// Create table and insert test data
	_, err = db.Exec(`
		CREATE TABLE books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL,
			isbn TEXT NOT NULL,
			created_at DATETIME NOT NULL,
			updated_at DATETIME NOT NULL
		)
	`)
	require.NoError(t, err)

	_, err = db.Exec("INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
		"Test Book", "Test Author", 2024, "1234567890", "2024-01-01", "2024-01-01")
	require.NoError(t, err)

	bookStore := model.NewBookStore(db)
	handler := NewBookHandler(bookStore)

	req := httptest.NewRequest("DELETE", "/books/1", nil)
	w := httptest.NewRecorder()
	req = mux.SetURLVars(req, map[string]string{"id": "1"})
	handler.DeleteBook(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)

	// Verify book was deleted
	book, err := bookStore.GetBook(1)
	assert.Nil(t, book)
	assert.Equal(t, "book not found", err.Error())
}
