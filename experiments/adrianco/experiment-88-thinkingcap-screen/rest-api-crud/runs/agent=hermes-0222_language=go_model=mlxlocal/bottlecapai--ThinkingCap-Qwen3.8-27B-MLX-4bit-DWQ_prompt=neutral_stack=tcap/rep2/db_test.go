package main

import (
	"errors"
	"path/filepath"
	"strconv"
	"testing"
)

func itoa(id int64) string { return strconv.FormatInt(id, 10) }

func openTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := NewStore(filepath.Join(t.TempDir(), "unit.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestStoreCRUDRoundTrip(t *testing.T) {
	s := openTestStore(t)

	b := &Book{Title: "Go in Action", Author: "William Kennedy", Year: 2019, ISBN: "978-1617284016"}
	if err := s.Create(b); err != nil {
		t.Fatalf("create: %v", err)
	}
	if b.ID == 0 {
		t.Fatal("create did not assign an id")
	}

	got, err := s.Get(b.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if *got != *b {
		t.Fatalf("get = %+v, want %+v", got, b)
	}

	got.Title = "Go in Action (2nd ed.)"
	got.Year = 2024
	if err := s.Update(got); err != nil {
		t.Fatalf("update: %v", err)
	}
	again, err := s.Get(got.ID)
	if err != nil {
		t.Fatalf("get after update: %v", err)
	}
	if again.Title != "Go in Action (2nd ed.)" || again.Year != 2024 {
		t.Fatalf("update not persisted: %+v", again)
	}

	books, err := s.List("")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(books) != 1 {
		t.Fatalf("list = %d books, want 1", len(books))
	}

	if err := s.Delete(again.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := s.Get(again.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("get after delete err = %v, want ErrNotFound", err)
	}
	if err := s.Delete(again.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("second delete err = %v, want ErrNotFound", err)
	}
}

func TestStoreListAuthorFilter(t *testing.T) {
	s := openTestStore(t)
	for _, b := range []*Book{
		{Title: "One", Author: "Tolkien"},
		{Title: "Two", Author: "tolkien"},
		{Title: "Three", Author: "Herbert"},
	} {
		if err := s.Create(b); err != nil {
			t.Fatalf("create: %v", err)
		}
	}
	books, err := s.List("TOLKIEN")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("case-insensitive filter returned %d books, want 2", len(books))
	}
}

func TestStoreUpdateMissing(t *testing.T) {
	s := openTestStore(t)
	err := s.Update(&Book{ID: 42, Title: "X", Author: "Y"})
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("update missing id err = %v, want ErrNotFound", err)
	}
}

func TestValidateBook(t *testing.T) {
	cases := []struct {
		name    string
		book    Book
		wantErr bool
	}{
		{"valid", Book{Title: "T", Author: "A"}, false},
		{"valid with year and isbn", Book{Title: "T", Author: "A", Year: 1999, ISBN: "x"}, false},
		{"missing title", Book{Author: "A"}, true},
		{"missing author", Book{Title: "T"}, true},
		{"negative year", Book{Title: "T", Author: "A", Year: -1}, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := validateBook(&tc.book)
			if (err != nil) != tc.wantErr {
				t.Fatalf("validateBook(%+v) err = %v, wantErr %v", tc.book, err, tc.wantErr)
			}
		})
	}
}
