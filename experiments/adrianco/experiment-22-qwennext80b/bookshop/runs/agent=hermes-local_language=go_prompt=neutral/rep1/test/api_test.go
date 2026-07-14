package test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"testing"
	"time"

	"bookapi/handler"
	"bookapi/model"
	"github.com/gorilla/mux"
)

var serverURL = "http://localhost:8082"
var testStore *model.BookStore

func TestMain(m *testing.M) {
	// Initialize test database
	var err error
	testStore, err = model.NewBookStore("test_books.db")
	if err != nil {
		fmt.Printf("Failed to initialize test database: %v\n", err)
		os.Exit(1)
	}

	// Clean up before running tests
	testStore.DeleteBook(1)
	testStore.DeleteBook(2)
	testStore.DeleteBook(3)
	testStore.DeleteBook(100)

	// Set up router
	bh := handler.NewBookHandler(testStore)
	router := mux.NewRouter()
	router.HandleFunc("/health", bh.HealthCheck)
	router.HandleFunc("/books", bh.ListBooks).Methods("GET")
	router.HandleFunc("/books", bh.CreateBook).Methods("POST")
	router.HandleFunc("/books/{id}", bh.GetBook).Methods("GET")
	router.HandleFunc("/books/{id}", bh.UpdateBook).Methods("PUT")
	router.HandleFunc("/books/{id}", bh.DeleteBook).Methods("DELETE")

	// Start server in background
	go func() {
		http.ListenAndServe(":8082", router)
	}()

	// Wait for server to start
	time.Sleep(2 * time.Second)

	code := m.Run()

	// Clean up after tests
	testStore.Close()
	os.Remove("test_books.db")
	os.Exit(code)
}

func TestHealthCheck(t *testing.T) {
	resp, err := http.Get(serverURL + "/health")
	if err != nil {
		t.Fatalf("Health check request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var result map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if result["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", result["status"])
	}
}

func TestCreateBook(t *testing.T) {
	book := model.Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2024,
		ISBN:   "978-0-123456-78-9",
	}

	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	resp, err := http.Post(serverURL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Create book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		t.Errorf("Expected status 201, got %d", resp.StatusCode)
	}

	var createdBook model.Book
	if err := json.NewDecoder(resp.Body).Decode(&createdBook); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if createdBook.Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", createdBook.Title)
	}
	if createdBook.Author != "Test Author" {
		t.Errorf("Expected author 'Test Author', got '%s'", createdBook.Author)
	}
	if createdBook.Year != 2024 {
		t.Errorf("Expected year 2024, got %d", createdBook.Year)
	}
	if createdBook.ISBN != "978-0-123456-78-9" {
		t.Errorf("Expected ISBN '978-0-123456-78-9', got '%s'", createdBook.ISBN)
	}
	if createdBook.ID == 0 {
		t.Error("Expected non-zero ID after creation")
	}
}

func TestCreateBookValidation(t *testing.T) {
	// Missing title
	book := model.Book{
		Author: "Test Author",
		Year:   2024,
		ISBN:   "978-0-123456-78-9",
	}

	jsonData, err := json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	resp, err := http.Post(serverURL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Create book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status 400 for validation error, got %d", resp.StatusCode)
	}

	// Missing author
	book = model.Book{
		Title:  "Test Book",
		Year:   2024,
		ISBN:   "978-0-123456-78-9",
	}

	jsonData, err = json.Marshal(book)
	if err != nil {
		t.Fatalf("Failed to marshal book: %v", err)
	}

	resp, err = http.Post(serverURL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Create book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("Expected status 400 for validation error, got %d", resp.StatusCode)
	}
}

func TestGetBook(t *testing.T) {
	// First create a book to get
	book := model.Book{
		Title:  "Get This Book",
		Author: "Get Author",
		Year:   2023,
		ISBN:   "978-0-123456-78-0",
	}
	jsonData, _ := json.Marshal(book)
	resp, err := http.Post(serverURL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Create book request failed: %v", err)
	}
	defer resp.Body.Close()

	var createdBook model.Book
	json.NewDecoder(resp.Body).Decode(&createdBook)

	resp, err = http.Get(serverURL + fmt.Sprintf("/books/%d", createdBook.ID))
	if err != nil {
		t.Fatalf("Get book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var retrievedBook model.Book
	if err := json.NewDecoder(resp.Body).Decode(&retrievedBook); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if retrievedBook.Title != "Get This Book" {
		t.Errorf("Expected title 'Get This Book', got '%s'", retrievedBook.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	resp, err := http.Get(serverURL + "/books/9999")
	if err != nil {
		t.Fatalf("Get book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404 for not found, got %d", resp.StatusCode)
	}
}

func TestListBooks(t *testing.T) {
	// Create some test books
	testStore.DeleteBook(1)
	testStore.DeleteBook(2)
	testStore.DeleteBook(3)

	book1 := model.Book{
		Title:  "Book One",
		Author: "Author A",
		Year:   2020,
		ISBN:   "978-0-123456-00-0",
	}
	book2 := model.Book{
		Title:  "Book Two",
		Author: "Author B",
		Year:   2021,
		ISBN:   "978-0-123456-00-1",
	}

	testStore.CreateBook(&book1)
	testStore.CreateBook(&book2)

	resp, err := http.Get(serverURL + "/books")
	if err != nil {
		t.Fatalf("List books request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var books []model.Book
	if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) < 2 {
		t.Errorf("Expected at least 2 books, got %d", len(books))
	}
}

func TestListBooksByAuthor(t *testing.T) {
	resp, err := http.Get(serverURL + "/books?author=Author")
	if err != nil {
		t.Fatalf("List books by author request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var books []model.Book
	if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(books) == 0 {
		t.Error("Expected at least 1 book from filter")
	}
}

func TestUpdateBook(t *testing.T) {
	// First create a book to update
	createBook := model.Book{
		Title:  "Original Title",
		Author: "Original Author",
		Year:   2020,
		ISBN:   "978-0-123456-00-2",
	}
	jsonData, _ := json.Marshal(createBook)
	resp, err := http.Post(serverURL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Create book request failed: %v", err)
	}
	defer resp.Body.Close()

	var createdBook model.Book
	json.NewDecoder(resp.Body).Decode(&createdBook)

	// Update the book
	updateBook := model.Book{
		ID:     createdBook.ID,
		Title:  "Updated Title",
		Author: "Updated Author",
		Year:   2024,
		ISBN:   "978-0-123456-00-2",
	}

	jsonData, err = json.Marshal(updateBook)
	if err != nil {
		t.Fatalf("Failed to marshal updated book: %v", err)
	}

	req, err := http.NewRequest(http.MethodPut, fmt.Sprintf("%s/books/%d", serverURL, createdBook.ID), bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Create request failed: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err = client.Do(req)
	if err != nil {
		t.Fatalf("Update book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var updatedBook model.Book
	if err := json.NewDecoder(resp.Body).Decode(&updatedBook); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if updatedBook.Title != "Updated Title" {
		t.Errorf("Expected title 'Updated Title', got '%s'", updatedBook.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	// First create a book to delete
	createBook := model.Book{
		Title:  "To Be Deleted",
		Author: "Delete Author",
		Year:   2020,
		ISBN:   "978-0-123456-00-3",
	}
	jsonData, _ := json.Marshal(createBook)
	resp, err := http.Post(serverURL+"/books", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		t.Fatalf("Create book request failed: %v", err)
	}
	defer resp.Body.Close()

	var createdBook model.Book
	json.NewDecoder(resp.Body).Decode(&createdBook)

	// Delete the book
	req, err := http.NewRequest(http.MethodDelete, fmt.Sprintf("%s/books/%d", serverURL, createdBook.ID), nil)
	if err != nil {
		t.Fatalf("Create request failed: %v", err)
	}

	client := &http.Client{}
	resp, err = client.Do(req)
	if err != nil {
		t.Fatalf("Delete book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNoContent {
		t.Errorf("Expected status 204, got %d", resp.StatusCode)
	}

	// Verify the book is gone
	resp, err = http.Get(fmt.Sprintf("%s/books/%d", serverURL, createdBook.ID))
	if err != nil {
		t.Fatalf("Get deleted book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404 after deletion, got %d", resp.StatusCode)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	req, err := http.NewRequest(http.MethodDelete, serverURL+"/books/9999", nil)
	if err != nil {
		t.Fatalf("Create request failed: %v", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Delete book request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404 for not found, got %d", resp.StatusCode)
	}
}
