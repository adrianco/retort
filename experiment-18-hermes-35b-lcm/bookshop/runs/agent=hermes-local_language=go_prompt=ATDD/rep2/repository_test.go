package main

import (
	"testing"
)

// Helper to create a fresh in-memory test repo
func newTestRepo(t *testing.T) *BookRepository {
	t.Helper()
	// Use a temp file path for SQLite
	dbPath := ":memory:"
	repo, err := NewBookRepository(dbPath)
	if err != nil {
		t.Fatalf("failed to create test repo: %v", err)
	}
	t.Cleanup(func() { repo.Close() })
	return repo
}

func TestCreateBook(t *testing.T) {
	repo := newTestRepo(t)

	book := &Book{
		Title:  "Clean Code",
		Author: "Robert Martin",
		Year:   2008,
		ISBN:   "978-0132350884",
	}

	err := repo.CreateBook(book)
	if err != nil {
		t.Fatalf("expected no error creating book, got: %v", err)
	}
	if book.ID == 0 {
		t.Error("expected auto-generated ID to be set")
	}
}

func TestGetBookByID(t *testing.T) {
	repo := newTestRepo(t)

	book := &Book{
		Title:  "The Pragmatic Programmer",
		Author: "David Thomas",
		Year:   1999,
		ISBN:   "978-0135957059",
	}
	if err := repo.CreateBook(book); err != nil {
		t.Fatalf("failed to create test book: %v", err)
	}

	got, err := repo.GetBookByID(book.ID)
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if got.Title != book.Title {
		t.Errorf("expected title %q, got %q", book.Title, got.Title)
	}
	if got.Author != book.Author {
		t.Errorf("expected author %q, got %q", book.Author, got.Author)
	}
}

func TestGetBookByID_NotFound(t *testing.T) {
	repo := newTestRepo(t)

	_, err := repo.GetBookByID(999)
	if err == nil {
		t.Fatal("expected error for non-existent book, got nil")
	}
}

func TestGetAllBooks(t *testing.T) {
	repo := newTestRepo(t)

	books := []*Book{
		{Title: "Book A", Author: "Alice", Year: 2020, ISBN: "111"},
		{Title: "Book B", Author: "Bob", Year: 2021, ISBN: "222"},
		{Title: "Book C", Author: "Alice", Year: 2022, ISBN: "333"},
	}
	for _, b := range books {
		if err := repo.CreateBook(b); err != nil {
			t.Fatalf("failed to create book: %v", err)
		}
	}

	all, err := repo.GetAllBooks("")
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if len(all) != 3 {
		t.Errorf("expected 3 books, got %d", len(all))
	}
}

func TestGetAllBooks_FilterByAuthor(t *testing.T) {
	repo := newTestRepo(t)

	books := []*Book{
		{Title: "Book A", Author: "Alice", Year: 2020, ISBN: "111"},
		{Title: "Book B", Author: "Bob", Year: 2021, ISBN: "222"},
		{Title: "Book C", Author: "Alice", Year: 2022, ISBN: "333"},
	}
	for _, b := range books {
		if err := repo.CreateBook(b); err != nil {
			t.Fatalf("failed to create book: %v", err)
		}
	}

	filtered, err := repo.GetAllBooks("Alice")
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("expected 2 books for author Alice, got %d", len(filtered))
	}
}

func TestGetAllBooks_Empty(t *testing.T) {
	repo := newTestRepo(t)

	books, err := repo.GetAllBooks("")
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if len(books) != 0 {
		t.Errorf("expected 0 books, got %d", len(books))
	}
}

func TestUpdateBook(t *testing.T) {
	repo := newTestRepo(t)

	book := &Book{
		Title:  "Original Title",
		Author: "Author",
		Year:   2020,
		ISBN:   "001",
	}
	if err := repo.CreateBook(book); err != nil {
		t.Fatalf("failed to create book: %v", err)
	}

	book.Title = "Updated Title"
	book.Year = 2021
	if err := repo.UpdateBook(book); err != nil {
		t.Fatalf("expected no error updating, got: %v", err)
	}

	got, err := repo.GetBookByID(book.ID)
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if got.Title != "Updated Title" {
		t.Errorf("expected title 'Updated Title', got %q", got.Title)
	}
	if got.Year != 2021 {
		t.Errorf("expected year 2021, got %d", got.Year)
	}
}

func TestDeleteBook(t *testing.T) {
	repo := newTestRepo(t)

	book := &Book{
		Title:  "To Delete",
		Author: "Author",
		Year:   2020,
		ISBN:   "002",
	}
	if err := repo.CreateBook(book); err != nil {
		t.Fatalf("failed to create book: %v", err)
	}

	if err := repo.DeleteBook(book.ID); err != nil {
		t.Fatalf("expected no error deleting, got: %v", err)
	}

	_, err := repo.GetBookByID(book.ID)
	if err == nil {
		t.Fatal("expected error after delete, got nil")
	}
}

func TestCloseRepo(t *testing.T) {
	repo := newTestRepo(t)
	if err := repo.Close(); err != nil {
		t.Fatalf("expected no error closing, got: %v", err)
	}
}

