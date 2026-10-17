package main

import (
	"errors"
	"path/filepath"
	"testing"
)

func TestStorePersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	s1, err := OpenStore(path)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	created, err := s1.Create(BookInput{Title: "Dune", Author: "Herbert", Year: 1965})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if err := s1.Close(); err != nil {
		t.Fatalf("close: %v", err)
	}

	s2, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer s2.Close()
	got, err := s2.Get(created.ID)
	if err != nil {
		t.Fatalf("get after reopen: %v", err)
	}
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestStoreNotFoundSentinels(t *testing.T) {
	s, err := OpenStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()

	if _, err := s.Get(1); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get err = %v", err)
	}
	if _, err := s.Update(1, BookInput{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Update err = %v", err)
	}
	if err := s.Delete(1); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Delete err = %v", err)
	}
}

func TestStoreISBNUniqueness(t *testing.T) {
	s, err := OpenStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()

	if _, err := s.Create(BookInput{Title: "A", Author: "X", ISBN: "1234567890"}); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Create(BookInput{Title: "B", Author: "Y", ISBN: "1234567890"}); !errors.Is(err, ErrISBNTaken) {
		t.Fatalf("duplicate create err = %v, want ErrISBNTaken", err)
	}
}

func TestStoreListEmptyIsNotNil(t *testing.T) {
	s, err := OpenStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()

	books, err := s.List("")
	if err != nil {
		t.Fatal(err)
	}
	if books == nil || len(books) != 0 {
		t.Fatalf("List() = %#v, want empty non-nil slice", books)
	}
}
