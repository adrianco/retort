package main

import (
	"os"
	"testing"
)

func TestBookStoreFunctions(t *testing.T) {
	// Create a test database
	store, err := NewBookStore()
	if err != nil {
		t.Fatal("Failed to initialize test database:", err)
	}
	defer store.Close()

	// Clean up test database after test
	defer func() {
		os.Remove("./books.db")
	}()

	// Test creating a book
	book := Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		Isbn:   "123-456-789",
	}

	createdBook, err := store.CreateBook(book)
	if err != nil {
		t.Fatal("Failed to create book:", err)
	}

	if createdBook.Title != book.Title {
		t.Errorf("Expected title %s, got %s", book.Title, createdBook.Title)
	}

	if createdBook.Author != book.Author {
		t.Errorf("Expected author %s, got %s", book.Author, createdBook.Author)
	}

	// Test getting the book by ID
	retrievedBook, err := store.GetBookByID(createdBook.ID)
	if err != nil {
		t.Fatal("Failed to get book:", err)
	}

	if retrievedBook.Title != book.Title {
		t.Errorf("Expected title %s, got %s", book.Title, retrievedBook.Title)
	}

	// Test updating the book
	updatedBook := Book{
		Title:  "Updated Test Book",
		Author: "Updated Test Author",
		Year:   2024,
		Isbn:   "987-654-321",
	}

	err = store.UpdateBook(createdBook.ID, updatedBook)
	if err != nil {
		t.Fatal("Failed to update book:", err)
	}

	// Verify update
	updatedRetrievedBook, err := store.GetBookByID(createdBook.ID)
	if err != nil {
		t.Fatal("Failed to get updated book:", err)
	}

	if updatedRetrievedBook.Title != updatedBook.Title {
		t.Errorf("Expected updated title %s, got %s", updatedBook.Title, updatedRetrievedBook.Title)
	}

	// Test deleting the book
	err = store.DeleteBook(createdBook.ID)
	if err != nil {
		t.Fatal("Failed to delete book:", err)
	}

	// Verify deletion
	_, err = store.GetBookByID(createdBook.ID)
	if err == nil {
		t.Error("Expected error when getting deleted book")
	}
}

func TestBookValidation(t *testing.T) {
	store, err := NewBookStore()
	if err != nil {
		t.Fatal("Failed to initialize test database:", err)
	}
	defer store.Close()

	// Clean up test database after test
	defer func() {
		os.Remove("./books.db")
	}()

	// Test creating a book with missing required fields
	book := Book{
		Title:  "", // Missing title
		Author: "Test Author",
		Year:   2023,
		Isbn:   "123-456-789",
	}

	_, err = store.CreateBook(book)
	if err == nil {
		t.Error("Expected error for missing title")
	}

	// Test creating a book with missing required fields (author)
	book2 := Book{
		Title:  "Test Book",
		Author: "", // Missing author
		Year:   2023,
		Isbn:   "123-456-789",
	}

	_, err = store.CreateBook(book2)
	if err == nil {
		t.Error("Expected error for missing author")
	}
}

func TestGetAllBooks(t *testing.T) {
	store, err := NewBookStore()
	if err != nil {
		t.Fatal("Failed to initialize test database:", err)
	}
	defer store.Close()

	// Clean up test database after test
	defer func() {
		os.Remove("./books.db")
	}()

	// Create test books
	book1 := Book{
		Title:  "Book One",
		Author: "Author A",
		Year:   2020,
		Isbn:   "111-111-111",
	}

	book2 := Book{
		Title:  "Book Two",
		Author: "Author B",
		Year:   2021,
		Isbn:   "222-222-222",
	}

	book3 := Book{
		Title:  "Book Three",
		Author: "Author A",
		Year:   2022,
		Isbn:   "333-333-333",
	}

	store.CreateBook(book1)
	store.CreateBook(book2)
	store.CreateBook(book3)

	// Test getting all books
	books, err := store.GetAllBooks("")
	if err != nil {
		t.Fatal("Failed to get all books:", err)
	}

	if len(books) != 3 {
		t.Errorf("Expected 3 books, got %d", len(books))
	}

	// Test filtering by author
	booksByAuthor, err := store.GetAllBooks("Author A")
	if err != nil {
		t.Fatal("Failed to get books by author:", err)
	}

	if len(booksByAuthor) != 2 {
		t.Errorf("Expected 2 books by Author A, got %d", len(booksByAuthor))
	}
}