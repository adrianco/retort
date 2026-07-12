package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"

	"github.com/gorilla/mux"
)

// TestMain sets up a shared test database
func TestMain(m *testing.M) {
	// Use a test database
	db, err := NewDatabase(":memory:")
	if err != nil {
		panic(err)
	}
	defer db.Close()
	
	if err := db.Init(); err != nil {
		panic(err)
	}

	// Set the global repo for tests
	bookRepo := NewBookRepository(db)
	bookHandler = NewBookHandler(bookRepo)

	os.Exit(m.Run())
}

var bookHandler *BookHandler

func createRouter() *mux.Router {
	router := mux.NewRouter()
	router.HandleFunc("/health", healthHandler).Methods("GET")
	router.HandleFunc("/books", bookHandler.CreateBook).Methods("POST")
	router.HandleFunc("/books", bookHandler.ListBooks).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.GetBook).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.UpdateBook).Methods("PUT")
	router.HandleFunc("/books/{id}", bookHandler.DeleteBook).Methods("DELETE")
	return router
}

func TestHealthHandler(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	
	router := createRouter()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var resp map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Errorf("Expected JSON response, got %s", w.Body.String())
	}
	
	if resp["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got %s", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	repo := NewBookRepository(db)
	handler := NewBookHandler(repo)
	
	// Test successful book creation
	body := bytes.NewBuffer([]byte(`{"title":"Test Book","author":"Test Author","year":2023,"isbn":"1234567890"}`))
	req := httptest.NewRequest("POST", "/books", body)
	w := httptest.NewRecorder()
	
	router := createRouter()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusCreated {
		t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
	}
	
	var book Book
	if err := json.Unmarshal(w.Body.Bytes(), &book); err != nil {
		t.Errorf("Expected JSON response, got %s", w.Body.String())
	}
	
	if book.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got %s", book.Title)
	}
	
	if book.Author != "Test Author" {
		t.Errorf("Expected author 'Test Author', got %s", book.Author)
	}
}

func TestCreateBookValidationError(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	repo := NewBookRepository(db)
	handler := NewBookHandler(repo)
	
	// Test missing title
	body := bytes.NewBuffer([]byte(`{"author":"Test Author","year":2023,"isbn":"1234567890"}`))
	req := httptest.NewRequest("POST", "/books", body)
	w := httptest.NewRecorder()
	
	router := createRouter()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d for validation error, got %d", http.StatusBadRequest, w.Code)
	}
	
	// Test missing author
	body = bytes.NewBuffer([]byte(`{"title":"Test Book","year":2023,"isbn":"1234567890"}`))
	req = httptest.NewRequest("POST", "/books", body)
	w = httptest.NewRecorder()
	
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d for validation error, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestListBooks(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	repo := NewBookRepository(db)
	
	// Create test books directly in the database
	book1 := &Book{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "111"}
	book2 := &Book{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "222"}
	book3 := &Book{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "333"}
	
	repo.Create(book1)
	repo.Create(book2)
	repo.Create(book3)
	
	// Test list all books - use a separate router with the same database
	router := mux.NewRouter()
	router.HandleFunc("/health", healthHandler).Methods("GET")
	router.HandleFunc("/books", bookHandler.ListBooks).Methods("GET")
	
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Errorf("Expected JSON response, got %s", w.Body.String())
	}
	
	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	repo := NewBookRepository(db)
	
	// Create test books
	book1 := &Book{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "111"}
	book2 := &Book{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "222"}
	book3 := &Book{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "333"}
	
	repo.Create(book1)
	repo.Create(book2)
	repo.Create(book3)
	
	// Test list books by author
	router := mux.NewRouter()
	router.HandleFunc("/health", healthHandler).Methods("GET")
	router.HandleFunc("/books", bookHandler.ListBooks).Methods("GET")
	
	req := httptest.NewRequest("GET", "/books?author=Author+A", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Errorf("Expected JSON response, got %s", w.Body.String())
	}
	
	if len(books) != 2 {
		t.Errorf("Expected 2 books by Author A, got %d", len(books))
	}
}

func TestGetBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	repo := NewBookRepository(db)
	
	// Create a test book directly in the database
	book := &Book{Title: "Test Book", Author: "Test Author", Year: 2023, ISBN: "1234567890"}
	repo.Create(book)
	fmt.Printf("Created book with ID: %d\n", book.ID)
	
	// Test get book by ID
	idStr := strconv.Itoa(book.ID)
	fmt.Printf("Requesting ID: %s\n", idStr)
	
	router := mux.NewRouter()
	router.HandleFunc("/health", healthHandler).Methods("GET")
	router.HandleFunc("/books", bookHandler.ListBooks).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.GetBook).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.UpdateBook).Methods("PUT")
	router.HandleFunc("/books/{id}", bookHandler.DeleteBook).Methods("DELETE")
	
	req := httptest.NewRequest("GET", "/books/"+idStr, nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	fmt.Printf("Response code: %d\n", w.Code)
	fmt.Printf("Response body: %s\n", w.Body.String())
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var gotBook Book
	if err := json.Unmarshal(w.Body.Bytes(), &gotBook); err != nil {
		t.Errorf("Expected JSON response, got %s", w.Body.String())
	}
	
	if gotBook.ID != book.ID {
		t.Errorf("Expected book ID %d, got %d", book.ID, gotBook.ID)
	}
	
	if gotBook.Title != book.Title {
		t.Errorf("Expected title %s, got %s", book.Title, gotBook.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	router := createRouter()
	req := httptest.NewRequest("GET", "/books/999", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	repo := NewBookRepository(db)
	
	// Create a test book
	book := &Book{Title: "Original Title", Author: "Original Author", Year: 2020, ISBN: "111"}
	repo.Create(book)
	
	// Test update book
	body := bytes.NewBuffer([]byte(`{"title":"Updated Title","author":"Updated Author","year":2021,"isbn":"999"}`))
	idStr := strconv.Itoa(book.ID)
	
	router := mux.NewRouter()
	router.HandleFunc("/health", healthHandler).Methods("GET")
	router.HandleFunc("/books", bookHandler.ListBooks).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.GetBook).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.UpdateBook).Methods("PUT")
	router.HandleFunc("/books/{id}", bookHandler.DeleteBook).Methods("DELETE")
	
	req := httptest.NewRequest("PUT", "/books/"+idStr, body)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}
	
	var updatedBook Book
	if err := json.Unmarshal(w.Body.Bytes(), &updatedBook); err != nil {
		t.Errorf("Expected JSON response, got %s", w.Body.String())
	}
	
	if updatedBook.Title != "Updated Title" {
		t.Errorf("Expected title 'Updated Title', got %s", updatedBook.Title)
	}
	
	if updatedBook.Year != 2021 {
		t.Errorf("Expected year 2021, got %d", updatedBook.Year)
	}
}

func TestDeleteBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	repo := NewBookRepository(db)
	
	// Create a test book
	book := &Book{Title: "To Delete", Author: "Delete Author", Year: 2023, ISBN: "DELETE1"}
	repo.Create(book)
	
	// Test delete book
	idStr := strconv.Itoa(book.ID)
	
	router := mux.NewRouter()
	router.HandleFunc("/health", healthHandler).Methods("GET")
	router.HandleFunc("/books", bookHandler.ListBooks).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.GetBook).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.UpdateBook).Methods("PUT")
	router.HandleFunc("/books/{id}", bookHandler.DeleteBook).Methods("DELETE")
	
	req := httptest.NewRequest("DELETE", "/books/"+idStr, nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusNoContent {
		t.Errorf("Expected status %d, got %d", http.StatusNoContent, w.Code)
	}
	
	// Verify book is deleted
	_, err = repo.GetByID(book.ID)
	if err == nil {
		t.Error("Expected book to be deleted")
	}
}

func TestInvalidBookID(t *testing.T) {
	router := createRouter()
	req := httptest.NewRequest("GET", "/books/invalid", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d for invalid ID, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestBookRepositoryOperations(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	
	repo := NewBookRepository(db)
	
	// Create
	book := &Book{Title: "Repo Test", Author: "Repo Author", Year: 2023, ISBN: "REPO1"}
	if err := repo.Create(book); err != nil {
		t.Fatal(err)
	}
	
	if book.ID == 0 {
		t.Error("Expected book ID to be set after creation")
	}
	
	// GetByID
	gotBook, err := repo.GetByID(book.ID)
	if err != nil {
		t.Fatal(err)
	}
	
	if gotBook.ID != book.ID {
		t.Errorf("Expected book ID %d, got %d", book.ID, gotBook.ID)
	}
	
	// Update
	gotBook.Title = "Updated by Repo"
	if err := repo.Update(gotBook); err != nil {
		t.Fatal(err)
	}
	
	// Verify update
	updatedBook, err := repo.GetByID(book.ID)
	if err != nil {
		t.Fatal(err)
	}
	
	if updatedBook.Title != "Updated by Repo" {
		t.Errorf("Expected title 'Updated by Repo', got %s", updatedBook.Title)
	}
	
	// Delete
	if err := repo.Delete(book.ID); err != nil {
		t.Fatal(err)
	}
	
	// Verify delete
	_, err = repo.GetByID(book.ID)
	if err == nil {
		t.Error("Expected book to be deleted")
	}
}

func TestBookRepositoryList(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Init(); err != nil {
		t.Fatal(err)
	}
	
	repo := NewBookRepository(db)
	
	// Create test books
	repo.Create(&Book{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "A1"})
	repo.Create(&Book{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "B1"})
	repo.Create(&Book{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "A2"})
	
	// List all
	books, err := repo.List(map[string]string{})
	if err != nil {
		t.Fatal(err)
	}
	
	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}
	
	// List by author
	books, err = repo.List(map[string]string{"author": "Author A"})
	if err != nil {
		t.Fatal(err)
	}
	
	if len(books) != 2 {
		t.Errorf("Expected 2 books by Author A, got %d", len(books))
	}
}
