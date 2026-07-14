package main

import (
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore() error = %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestStoreCreateAndGetBook(t *testing.T) {
	s := newTestStore(t)

	b := Book{Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937, ISBN: "978-0345339683"}
	created, err := s.CreateBook(b)
	if err != nil {
		t.Fatalf("CreateBook() error = %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected created book to have non-zero ID")
	}

	got, err := s.GetBook(created.ID)
	if err != nil {
		t.Fatalf("GetBook() error = %v", err)
	}
	if got.Title != b.Title || got.Author != b.Author || got.Year != b.Year || got.ISBN != b.ISBN {
		t.Fatalf("GetBook() = %+v, want title/author/year/isbn to match %+v", got, b)
	}
}

func TestStoreGetBookNotFound(t *testing.T) {
	s := newTestStore(t)

	_, err := s.GetBook(999)
	if err != ErrNotFound {
		t.Fatalf("GetBook() error = %v, want ErrNotFound", err)
	}
}

func TestStoreListBooksFilterByAuthor(t *testing.T) {
	s := newTestStore(t)

	if _, err := s.CreateBook(Book{Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937, ISBN: "1"}); err != nil {
		t.Fatalf("CreateBook() error = %v", err)
	}
	if _, err := s.CreateBook(Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "2"}); err != nil {
		t.Fatalf("CreateBook() error = %v", err)
	}

	all, err := s.ListBooks("")
	if err != nil {
		t.Fatalf("ListBooks() error = %v", err)
	}
	if len(all) != 2 {
		t.Fatalf("ListBooks(\"\") returned %d books, want 2", len(all))
	}

	filtered, err := s.ListBooks("Frank Herbert")
	if err != nil {
		t.Fatalf("ListBooks() error = %v", err)
	}
	if len(filtered) != 1 || filtered[0].Author != "Frank Herbert" {
		t.Fatalf("ListBooks(\"Frank Herbert\") = %+v, want single book by Frank Herbert", filtered)
	}
}

func TestStoreUpdateBook(t *testing.T) {
	s := newTestStore(t)

	created, err := s.CreateBook(Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "2"})
	if err != nil {
		t.Fatalf("CreateBook() error = %v", err)
	}

	updated := Book{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969, ISBN: "3"}
	result, err := s.UpdateBook(created.ID, updated)
	if err != nil {
		t.Fatalf("UpdateBook() error = %v", err)
	}
	if result.Title != "Dune Messiah" || result.Year != 1969 {
		t.Fatalf("UpdateBook() = %+v, want updated fields", result)
	}

	got, err := s.GetBook(created.ID)
	if err != nil {
		t.Fatalf("GetBook() error = %v", err)
	}
	if got.Title != "Dune Messiah" {
		t.Fatalf("GetBook() after update = %+v, want title Dune Messiah", got)
	}
}

func TestStoreUpdateBookNotFound(t *testing.T) {
	s := newTestStore(t)

	_, err := s.UpdateBook(999, Book{Title: "X", Author: "Y"})
	if err != ErrNotFound {
		t.Fatalf("UpdateBook() error = %v, want ErrNotFound", err)
	}
}

func TestStoreDeleteBook(t *testing.T) {
	s := newTestStore(t)

	created, err := s.CreateBook(Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "2"})
	if err != nil {
		t.Fatalf("CreateBook() error = %v", err)
	}

	if err := s.DeleteBook(created.ID); err != nil {
		t.Fatalf("DeleteBook() error = %v", err)
	}

	_, err = s.GetBook(created.ID)
	if err != ErrNotFound {
		t.Fatalf("GetBook() after delete error = %v, want ErrNotFound", err)
	}
}

func TestStoreDeleteBookNotFound(t *testing.T) {
	s := newTestStore(t)

	err := s.DeleteBook(999)
	if err != ErrNotFound {
		t.Fatalf("DeleteBook() error = %v, want ErrNotFound", err)
	}
}
