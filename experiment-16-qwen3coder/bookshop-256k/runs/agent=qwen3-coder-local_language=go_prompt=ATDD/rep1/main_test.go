package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// Helper function to create a test server
func createTestServer(t *testing.T) *httptest.Server {
	// Initialize database for testing
	db, err := initDB()
	if err != nil {
		t.Fatalf("Failed to initialize test database: %v", err)
	}
	defer db.Close()

	// Initialize repository and service
	repo := NewBookRepository(db)
	service := NewBookService(repo)

	// Create test server
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Route("/books", func(r chi.Router) {
		r.Post("/", service.CreateBookHandler)
		r.Get("/", service.ListBooksHandler)
		r.Route("/{id}", func(r chi.Router) {
			r.Get("/", service.GetBookHandler)
			r.Put("/", service.UpdateBookHandler)
			r.Delete("/", service.DeleteBookHandler)
		})
	})

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	return httptest.NewServer(r)
}

// Test creating a book
func TestCreateBook(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Test valid book creation
	bookData := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}

	jsonData, _ := json.Marshal(bookData)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, resp.StatusCode)
	}

	var response BookResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if response.Book.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got '%s'", response.Book.Title)
	}
	if response.Book.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got '%s'", response.Book.Author)
	}
	if response.Book.Year != 1925 {
		t.Errorf("Expected year 1925, got %d", response.Book.Year)
	}
	if response.Book.ISBN != "978-0-7432-7356-5" {
		t.Errorf("Expected ISBN '978-0-7432-7356-5', got '%s'", response.Book.ISBN)
	}
}

// Test creating a book without required fields
func TestCreateBookMissingRequiredFields(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Test missing title
	bookData := map[string]interface{}{
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}

	jsonData, _ := json.Marshal(bookData)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, resp.StatusCode)
	}
}

// Test creating a book with duplicate ISBN
func TestCreateBookDuplicateISBN(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// First create a book
	bookData := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}

	jsonData, _ := json.Marshal(bookData)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}
	defer resp.Body.Close()

	// Now try to create another book with same ISBN
	resp2, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}
	defer resp2.Body.Close()

	if resp2.StatusCode != http.StatusConflict {
		t.Errorf("Expected status %d, got %d", http.StatusConflict, resp2.StatusCode)
	}
}

// Test listing all books
func TestListBooks(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Create some books
	book1 := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}
	book2 := map[string]interface{}{
		"title":  "To Kill a Mockingbird",
		"author": "Harper Lee",
		"year":   1960,
		"isbn":   "978-0-06-112008-4",
	}

	jsonData1, _ := json.Marshal(book1)
	http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData1))

	jsonData2, _ := json.Marshal(book2)
	http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData2))

	// List all books
	resp, err := http.Get(ts.URL+"/books")
	if err != nil {
		t.Fatalf("Failed to list books: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, resp.StatusCode)
	}

	var response BooksResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(response.Books) != 2 {
		t.Errorf("Expected 2 books, got %d", len(response.Books))
	}
}

// Test listing books by author
func TestListBooksByAuthor(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Create some books
	book1 := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}
	book2 := map[string]interface{}{
		"title":  "To Kill a Mockingbird",
		"author": "Harper Lee",
		"year":   1960,
		"isbn":   "978-0-06-112008-4",
	}
	book3 := map[string]interface{}{
		"title":  "The Catcher in the Rye",
		"author": "J.D. Salinger",
		"year":   1951,
		"isbn":   "978-0-316-76948-0",
	}

	jsonData1, _ := json.Marshal(book1)
	http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData1))

	jsonData2, _ := json.Marshal(book2)
	http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData2))

	jsonData3, _ := json.Marshal(book3)
	http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData3))

	// List books by author
	resp, err := http.Get(ts.URL+"/books?author=F. Scott Fitzgerald")
	if err != nil {
		t.Fatalf("Failed to list books: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, resp.StatusCode)
	}

	var response BooksResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(response.Books) != 1 {
		t.Errorf("Expected 1 book for author, got %d", len(response.Books))
	}
	if response.Books[0].Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got '%s'", response.Books[0].Author)
	}
}

// Test getting a single book by ID
func TestGetBook(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Create a book
	bookData := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}

	jsonData, _ := json.Marshal(bookData)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}
	defer resp.Body.Close()

	// Extract the book ID from the response
	var createdBook BookResponse
	if err := json.NewDecoder(resp.Body).Decode(&createdBook); err != nil {
		t.Fatalf("Failed to decode created book response: %v", err)
	}

	// Get the book by ID
	resp2, err := http.Get(fmt.Sprintf("%s/books/%d", ts.URL, createdBook.Book.ID))
	if err != nil {
		t.Fatalf("Failed to get book: %v", err)
	}
	defer resp2.Body.Close()

	if resp2.StatusCode != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, resp2.StatusCode)
	}

	var response BookResponse
	if err := json.NewDecoder(resp2.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if response.Book.Title != "The Great Gatsby" {
		t.Errorf("Expected title 'The Great Gatsby', got '%s'", response.Book.Title)
	}
	if response.Book.Author != "F. Scott Fitzgerald" {
		t.Errorf("Expected author 'F. Scott Fitzgerald', got '%s'", response.Book.Author)
	}
}

// Test getting a non-existent book
func TestGetBookNotFound(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Try to get a non-existent book
	resp, err := http.Get(ts.URL + "/books/999")
	if err != nil {
		t.Fatalf("Failed to get book: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, resp.StatusCode)
	}
}

// Test updating a book
func TestUpdateBook(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Create a book
	bookData := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}

	jsonData, _ := json.Marshal(bookData)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}
	defer resp.Body.Close()

	// Extract the book ID from the response
	var createdBook BookResponse
	if err := json.NewDecoder(resp.Body).Decode(&createdBook); err != nil {
		t.Fatalf("Failed to decode created book response: %v", err)
	}

	// Update the book
	updateData := map[string]interface{}{
		"title":  "The Great Gatsby: Revised Edition",
		"author": "F. Scott Fitzgerald",
		"year":   1926,
		"isbn":   "978-0-7432-7356-6",
	}

	jsonData2, _ := json.Marshal(updateData)
	req, _ := http.NewRequest("PUT", fmt.Sprintf("%s/books/%d", ts.URL, createdBook.Book.ID), bytes.NewBuffer(jsonData2))
	req.Header.Set("Content-Type", "application/json")
	resp2, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Failed to update book: %v", err)
	}
	defer resp2.Body.Close()

	if resp2.StatusCode != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, resp2.StatusCode)
	}

	var response BookResponse
	if err := json.NewDecoder(resp2.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if response.Book.Title != "The Great Gatsby: Revised Edition" {
		t.Errorf("Expected updated title 'The Great Gatsby: Revised Edition', got '%s'", response.Book.Title)
	}
	if response.Book.Year != 1926 {
		t.Errorf("Expected updated year 1926, got %d", response.Book.Year)
	}
}

// Test updating a non-existent book
func TestUpdateBookNotFound(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Try to update a non-existent book
	updateData := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}

	jsonData, _ := json.Marshal(updateData)
	req, _ := http.NewRequest("PUT", ts.URL+"/books/999", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Failed to update book: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, resp.StatusCode)
	}
}

// Test deleting a book
func TestDeleteBook(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Create a book
	bookData := map[string]interface{}{
		"title":  "The Great Gatsby",
		"author": "F. Scott Fitzgerald",
		"year":   1925,
		"isbn":   "978-0-7432-7356-5",
	}

	jsonData, _ := json.Marshal(bookData)
	resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Failed to create book: %v", err)
	}
	defer resp.Body.Close()

	// Extract the book ID from the response
	var createdBook BookResponse
	if err := json.NewDecoder(resp.Body).Decode(&createdBook); err != nil {
		t.Fatalf("Failed to decode created book response: %v", err)
	}

	// Delete the book
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("%s/books/%d", ts.URL, createdBook.Book.ID), nil)
	resp2, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Failed to delete book: %v", err)
	}
	defer resp2.Body.Close()

	if resp2.StatusCode != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d", http.StatusNoContent, resp2.StatusCode)
	}
}

// Test deleting a non-existent book
func TestDeleteBookNotFound(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	// Try to delete a non-existent book
	req, _ := http.NewRequest("DELETE", ts.URL+"/books/999", nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Failed to delete book: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, resp.StatusCode)
	}
}

// Test health endpoint
func TestHealthEndpoint(t *testing.T) {
	ts := createTestServer(t)
	defer ts.Close()

	resp, err := http.Get(ts.URL + "/health")
	if err != nil {
		t.Fatalf("Failed to get health: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("Failed to read response body: %v", err)
	}

	if string(body) != "OK" {
		t.Errorf("Expected body 'OK', got '%s'", string(body))
	}
}