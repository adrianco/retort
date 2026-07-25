package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupTestDB(t *testing.T) *DB {
	t.Helper()
	
	// Use a temporary in-memory database for testing
	db, err := NewDB(":memory:")
	require.NoError(t, err, "Failed to create test database")
	
	return db
}

func teardownTestDB(db *DB) {
	db.Close()
}

func TestHealthHandler(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code, "Health endpoint should return 200")
	
	var healthResp HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &healthResp)
	require.NoError(t, err, "Failed to unmarshal health response")
	
	assert.Equal(t, "healthy", healthResp.Status, "Health status should be healthy")
	assert.NotZero(t, healthResp.Timestamp.Unix(), "Timestamp should be set")
}

func TestCreateBook(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	book := BookInput{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}
	
	body, err := json.Marshal(book)
	require.NoError(t, err, "Failed to marshal book")
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	w := httptest.NewRecorder()
	
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code, "Create book should return 201")
	
	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	require.NoError(t, err, "Failed to unmarshal created book")
	
	assert.Equal(t, book.Title, createdBook.Title, "Title should match")
	assert.Equal(t, book.Author, createdBook.Author, "Author should match")
	assert.Equal(t, book.Year, createdBook.Year, "Year should match")
	assert.Equal(t, book.ISBN, createdBook.ISBN, "ISBN should match")
	assert.NotZero(t, createdBook.ID, "ID should be set")
	assert.NotZero(t, createdBook.CreatedAt.Unix(), "CreatedAt should be set")
}

func TestCreateBookValidation(t *testing.T) {
	testCases := []struct {
		name     string
		book     BookInput
		statusCode int
	}{
		{
			name:     "Missing title",
			book:     BookInput{Author: "Test Author", Year: 2000, ISBN: "123"},
			statusCode: http.StatusBadRequest,
		},
		{
			name:     "Missing author",
			book:     BookInput{Title: "Test Title", Year: 2000, ISBN: "123"},
			statusCode: http.StatusBadRequest,
		},
		{
			name:     "Empty title",
			book:     BookInput{Title: "", Author: "Test Author"},
			statusCode: http.StatusBadRequest,
		},
		{
			name:     "Empty author",
			book:     BookInput{Title: "Test Title", Author: ""},
			statusCode: http.StatusBadRequest,
		},
	}
	
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			body, err := json.Marshal(tc.book)
			require.NoError(t, err, "Failed to marshal book")
			
			req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
			w := httptest.NewRecorder()
			
			server.router.ServeHTTP(w, req)
			
			assert.Equal(t, tc.statusCode, w.Code, "Should return %d", tc.statusCode)
		})
	}
}

func TestGetBook(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	// First create a book
	book := BookInput{
		Title:  "1984",
		Author: "George Orwell",
		Year:   1949,
		ISBN:   "978-0451524935",
	}
	
	body, err := json.Marshal(book)
	require.NoError(t, err, "Failed to marshal book")
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	require.NoError(t, err, "Failed to unmarshal created book")
	
	// Now get the book
	req = httptest.NewRequest("GET", "/books/"+string(rune('0'+createdBook.ID)), nil)
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code, "Get book should return 200")
	
	var retrievedBook Book
	err = json.Unmarshal(w.Body.Bytes(), &retrievedBook)
	require.NoError(t, err, "Failed to unmarshal retrieved book")
	
	assert.Equal(t, createdBook.ID, retrievedBook.ID, "IDs should match")
	assert.Equal(t, createdBook.Title, retrievedBook.Title, "Titles should match")
}

func TestGetBookNotFound(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	req := httptest.NewRequest("GET", "/books/99999", nil)
	w := httptest.NewRecorder()
	
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusNotFound, w.Code, "Get non-existent book should return 404")
}

func TestUpdateBook(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	// First create a book
	book := BookInput{
		Title:  "To Kill a Mockingbird",
		Author: "Harper Lee",
		Year:   1960,
		ISBN:   "978-0061120084",
	}
	
	body, err := json.Marshal(book)
	require.NoError(t, err, "Failed to marshal book")
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	require.NoError(t, err, "Failed to unmarshal created book")
	
	// Now update the book
	updatedBook := BookInput{
		Title:  "To Kill a Mockingbird (Updated)",
		Author: "Harper Lee",
		Year:   1960,
		ISBN:   "978-0061120084",
	}
	
	body, err = json.Marshal(updatedBook)
	require.NoError(t, err, "Failed to marshal updated book")
	
	req = httptest.NewRequest("PUT", "/books/"+string(rune('0'+createdBook.ID)), bytes.NewBuffer(body))
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code, "Update book should return 200")
	
	var retrievedBook Book
	err = json.Unmarshal(w.Body.Bytes(), &retrievedBook)
	require.NoError(t, err, "Failed to unmarshal retrieved book")
	
	assert.Equal(t, createdBook.ID, retrievedBook.ID, "IDs should match")
	assert.Equal(t, updatedBook.Title, retrievedBook.Title, "Updated title should match")
}

func TestDeleteBook(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	// First create a book
	book := BookInput{
		Title:  "Pride and Prejudice",
		Author: "Jane Austen",
		Year:   1813,
		ISBN:   "978-0141439518",
	}
	
	body, err := json.Marshal(book)
	require.NoError(t, err, "Failed to marshal book")
	
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	var createdBook Book
	err = json.Unmarshal(w.Body.Bytes(), &createdBook)
	require.NoError(t, err, "Failed to unmarshal created book")
	
	// Now delete the book
	req = httptest.NewRequest("DELETE", "/books/"+string(rune('0'+createdBook.ID)), nil)
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusNoContent, w.Code, "Delete book should return 204")
	
	// Verify the book is gone
	req = httptest.NewRequest("GET", "/books/"+string(rune('0'+createdBook.ID)), nil)
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusNotFound, w.Code, "Deleted book should return 404")
}

func TestListBooks(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	// Create some books
	books := []BookInput{
		{Title: "Book 1", Author: "Author A", Year: 2000},
		{Title: "Book 2", Author: "Author B", Year: 2001},
		{Title: "Book 3", Author: "Author A", Year: 2002},
	}
	
	for _, book := range books {
		body, err := json.Marshal(book)
		require.NoError(t, err, "Failed to marshal book")
		
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		w := httptest.NewRecorder()
		server.router.ServeHTTP(w, req)
		require.Equal(t, http.StatusCreated, w.Code, "Create should return 201")
	}
	
	// List all books
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code, "List books should return 200")
	
	var retrievedBooks []Book
	err := json.Unmarshal(w.Body.Bytes(), &retrievedBooks)
	require.NoError(t, err, "Failed to unmarshal books")
	
	assert.Len(t, retrievedBooks, 3, "Should have 3 books")
}

func TestListBooksByAuthor(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	// Create some books
	books := []BookInput{
		{Title: "Book 1", Author: "Author A", Year: 2000},
		{Title: "Book 2", Author: "Author B", Year: 2001},
		{Title: "Book 3", Author: "Author A", Year: 2002},
	}
	
	for _, book := range books {
		body, err := json.Marshal(book)
		require.NoError(t, err, "Failed to marshal book")
		
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		w := httptest.NewRecorder()
		server.router.ServeHTTP(w, req)
		require.Equal(t, http.StatusCreated, w.Code, "Create should return 201")
	}
	
	// List books by author
	req := httptest.NewRequest("GET", "/books?author=Author+A", nil)
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code, "List books by author should return 200")
	
	var retrievedBooks []Book
	err := json.Unmarshal(w.Body.Bytes(), &retrievedBooks)
	require.NoError(t, err, "Failed to unmarshal books")
	
	assert.Len(t, retrievedBooks, 2, "Should have 2 books by Author A")
	
	// Verify all returned books have the correct author
	for _, book := range retrievedBooks {
		assert.Contains(t, book.Author, "Author A", "Book author should contain 'Author A'")
	}
}

func TestGetBooksByAuthor(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	// Create some books
	books := []BookInput{
		{Title: "Book 1", Author: "Author A", Year: 2000},
		{Title: "Book 2", Author: "Author B", Year: 2001},
		{Title: "Book 3", Author: "Author A", Year: 2002},
	}
	
	for _, book := range books {
		_, err := db.CreateBook(&book)
		require.NoError(t, err, "Failed to create book")
	}
	
	// Test GetBooksByAuthor
	retrievedBooks, err := db.GetBooksByAuthor("Author A")
	require.NoError(t, err, "GetBooksByAuthor should succeed")
	
	assert.Len(t, retrievedBooks, 2, "Should have 2 books by Author A")
	
	// Test case-insensitive search
	retrievedBooks, err = db.GetBooksByAuthor("author a")
	require.NoError(t, err, "GetBooksByAuthor should succeed with lowercase")
	
	assert.Len(t, retrievedBooks, 2, "Should have 2 books by Author A (case insensitive)")
}

func TestDeleteNonExistentBook(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(db)
	
	server := NewServer(db)
	
	req := httptest.NewRequest("DELETE", "/books/99999", nil)
	w := httptest.NewRecorder()
	
	server.router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusNotFound, w.Code, "Delete non-existent book should return 404")
}
