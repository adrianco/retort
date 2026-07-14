package main

import (
	"os"
	"testing"
)

func TestBookStoreFunctions(t *testing.T) {
	// Create a temporary database for testing
	dbPath := "./test_books.db"
	store, err := NewBookStore(dbPath)
	if err != nil {
		t.Fatal("Failed to create test database:", err)
	}
	defer store.Close()
	defer os.Remove(dbPath)

	// Test creating a book
	book := &Book{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2023,
		ISBN:   "123-456-789",
	}

	err = store.CreateBook(book)
	if err != nil {
		t.Fatal("Failed to create book:", err)
	}

	// Test getting all books
	books, err := store.GetAllBooks("")
	if err != nil {
		t.Fatal("Failed to get books:", err)
	}

	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}

	// Test getting by ID
	retrievedBook, err := store.GetBookByID(1)
	if err != nil {
		t.Fatal("Failed to get book by ID:", err)
	}

	if retrievedBook.Title != book.Title {
		t.Errorf("Expected title %s, got %s", book.Title, retrievedBook.Title)
	}

	// Test updating
	updatedBook := &Book{
		Title:  "Updated Test Book",
		Author: "Updated Test Author",
		Year:   2024,
		ISBN:   "987-654-321",
	}
	
	err = store.UpdateBook(1, updatedBook)
	if err != nil {
		t.Fatal("Failed to update book:", err)
	}

	retrievedBook, err = store.GetBookByID(1)
	if err != nil {
		t.Fatal("Failed to get updated book:", err)
	}

	if retrievedBook.Title != updatedBook.Title {
		t.Errorf("Expected updated title %s, got %s", updatedBook.Title, retrievedBook.Title)
	}

	// Test deleting
	err = store.DeleteBook(1)
	if err != nil {
		t.Fatal("Failed to delete book:", err)
	}

	// Verify deletion
	_, err = store.GetBookByID(1)
	if err == nil {
		t.Error("Expected error when getting deleted book")
	}
}

func TestBookStoreFilter(t *testing.T) {
	// Create a temporary database for testing
	dbPath := "./test_filter.db"
	store, err := NewBookStore(dbPath)
	if err != nil {
		t.Fatal("Failed to create test database:", err)
	}
	defer store.Close()
	defer os.Remove(dbPath)

	// Create multiple books
	book1 := &Book{
		Title:  "Book 1",
		Author: "Author A",
		Year:   2020,
		ISBN:   "111-111-111",
	}

	book2 := &Book{
		Title:  "Book 2",
		Author: "Author B",
		Year:   2021,
		ISBN:   "222-222-222",
	}

	book3 := &Book{
		Title:  "Book 3",
		Author: "Author A",
		Year:   2022,
		ISBN:   "333-333-333",
	}

	store.CreateBook(book1)
	store.CreateBook(book2)
	store.CreateBook(book3)

	// Test filtering by author
	books, err := store.GetAllBooks("Author A")
	if err != nil {
		t.Fatal("Failed to get books by author:", err)
	}

	if len(books) != 2 {
		t.Errorf("Expected 2 books by Author A, got %d", len(books))
	}

	// Verify all books are from Author A
	for _, book := range books {
		if book.Author != "Author A" {
			t.Errorf("Expected book by Author A, got book by %s", book.Author)
		}
	}
}

func TestBookStoreEmptyFilter(t *testing.T) {
	// Create a temporary database for testing
	dbPath := "./test_empty.db"
	store, err := NewBookStore(dbPath)
	if err != nil {
		t.Fatal("Failed to create test database:", err)
	}
	defer store.Close()
	defer os.Remove(dbPath)

	// Test with no books
	books, err := store.GetAllBooks("")
	if err != nil {
		t.Fatal("Failed to get books:", err)
	}

	if len(books) != 0 {
		t.Errorf("Expected 0 books, got %d", len(books))
	}
}