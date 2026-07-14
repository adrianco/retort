package main

import (
	"testing"
)

func TestDatabase_CreateAndReadBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create database: %v", err)
	}
	defer db.Close()

	book := &Book{Title: "Test Book", Author: "Test Author", Year: 2023, ISBN: "123"}
	if err := db.CreateBook(book); err != nil {
		t.Fatalf("create failed: %v", err)
	}

	if book.ID != 1 {
		t.Errorf("expected ID 1, got %d", book.ID)
	}

	fetched, err := db.GetBook(1)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}

	if fetched.Title != "Test Book" {
		t.Errorf("expected title 'Test Book', got %q", fetched.Title)
	}
	if fetched.Author != "Test Author" {
		t.Errorf("expected author 'Test Author', got %q", fetched.Author)
	}
	if fetched.Year != 2023 {
		t.Errorf("expected year 2023, got %d", fetched.Year)
	}
	if fetched.ISBN != "123" {
		t.Errorf("expected isbn '123', got %q", fetched.ISBN)
	}
}

func TestDatabase_GetNonExistentBookReturnsError(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create database: %v", err)
	}
	defer db.Close()

	_, err = db.GetBook(999)
	if err == nil {
		t.Fatal("expected error for non-existent book, got nil")
	}
}

func TestDatabase_UpdateBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create database: %v", err)
	}
	defer db.Close()

	book := &Book{Title: "Old Title", Author: "Old Author", Year: 2000, ISBN: "old"}
	if err := db.CreateBook(book); err != nil {
		t.Fatalf("create failed: %v", err)
	}

	book.Title = "New Title"
	book.ISBN = "new"
	if err := db.UpdateBook(book); err != nil {
		t.Fatalf("update failed: %v", err)
	}

	fetched, err := db.GetBook(1)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}

	if fetched.Title != "New Title" {
		t.Errorf("expected title 'New Title', got %q", fetched.Title)
	}
	if fetched.ISBN != "new" {
		t.Errorf("expected isbn 'new', got %q", fetched.ISBN)
	}
}

func TestDatabase_DeleteBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create database: %v", err)
	}
	defer db.Close()

	book := &Book{Title: "ToDelete", Author: "Author", Year: 2020, ISBN: "x"}
	if err := db.CreateBook(book); err != nil {
		t.Fatalf("create failed: %v", err)
	}

	if err := db.DeleteBook(1); err != nil {
		t.Fatalf("delete failed: %v", err)
	}

	_, err = db.GetBook(1)
	if err == nil {
		t.Fatal("expected error after delete, got nil")
	}
}

func TestDatabase_ListBooksReturnsAll(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create database: %v", err)
	}
	defer db.Close()

	for _, b := range []*Book{
		{Title: "Book A", Author: "Author A", Year: 2010, ISBN: "a"},
		{Title: "Book B", Author: "Author B", Year: 2015, ISBN: "b"},
	} {
		if err := db.CreateBook(b); err != nil {
			t.Fatalf("create failed: %v", err)
		}
	}

	books, err := db.ListBooks()
	if err != nil {
		t.Fatalf("list failed: %v", err)
	}

	if len(books) != 2 {
		t.Errorf("expected 2 books, got %d", len(books))
	}
}

func TestDatabase_ListBooksByAuthor(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create database: %v", err)
	}
	defer db.Close()

	for _, b := range []*Book{
		{Title: "Book A", Author: "Author X", Year: 2010, ISBN: "a"},
		{Title: "Book B", Author: "Author Y", Year: 2015, ISBN: "b"},
		{Title: "Book C", Author: "Author X", Year: 2020, ISBN: "c"},
	} {
		if err := db.CreateBook(b); err != nil {
			t.Fatalf("create failed: %v", err)
		}
	}

	books, err := db.ListBooksByAuthor("Author X")
	if err != nil {
		t.Fatalf("list by author failed: %v", err)
	}

	if len(books) != 2 {
		t.Errorf("expected 2 books by Author X, got %d", len(books))
	}

	for _, b := range books {
		if b.Author != "Author X" {
			t.Errorf("expected author 'Author X', got %q", b.Author)
		}
	}
}

func TestDatabase_ListBooksByAuthorNoResults(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create database: %v", err)
	}
	defer db.Close()

	books, err := db.ListBooksByAuthor("Nobody")
	if err != nil {
		t.Fatalf("list by author failed: %v", err)
	}

	if len(books) != 0 {
		t.Errorf("expected 0 books, got %d", len(books))
	}
}
