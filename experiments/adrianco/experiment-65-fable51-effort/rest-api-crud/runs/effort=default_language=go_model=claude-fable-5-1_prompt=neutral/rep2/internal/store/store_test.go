package store

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := Open(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func intp(i int) *int { return &i }

func TestCRUDRoundTrip(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	created, err := s.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert", Year: intp(1965), ISBN: "9780441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != "Dune" || got.Author != "Frank Herbert" || got.Year == nil || *got.Year != 1965 || got.ISBN != "9780441172719" {
		t.Errorf("Get returned %+v", got)
	}

	updated, err := s.Update(ctx, created.ID, Book{Title: "Dune Messiah", Author: "Frank Herbert", Year: intp(1969)})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "Dune Messiah" || updated.ISBN != "" {
		t.Errorf("Update returned %+v", updated)
	}
	got, _ = s.Get(ctx, created.ID)
	if got.Title != "Dune Messiah" || *got.Year != 1969 || got.ISBN != "" {
		t.Errorf("after Update, Get returned %+v", got)
	}

	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: want ErrNotFound, got %v", err)
	}
}

func TestNotFoundErrors(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	if _, err := s.Get(ctx, 999); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: want ErrNotFound, got %v", err)
	}
	if _, err := s.Update(ctx, 999, Book{Title: "x", Author: "y"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: want ErrNotFound, got %v", err)
	}
	if err := s.Delete(ctx, 999); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: want ErrNotFound, got %v", err)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	seed := []Book{
		{Title: "Neuromancer", Author: "William Gibson", Year: intp(1984)},
		{Title: "Count Zero", Author: "William Gibson", Year: intp(1986)},
		{Title: "Snow Crash", Author: "Neal Stephenson", Year: intp(1992)},
		{Title: "Untitled", Author: "Anon"}, // no year, no isbn
	}
	for _, b := range seed {
		if _, err := s.Create(ctx, b); err != nil {
			t.Fatalf("Create %q: %v", b.Title, err)
		}
	}

	all, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 4 {
		t.Fatalf("List all: want 4, got %d", len(all))
	}
	if all[3].Year != nil {
		t.Errorf("expected nil year for book without year, got %d", *all[3].Year)
	}
	for i := 1; i < len(all); i++ {
		if all[i].ID <= all[i-1].ID {
			t.Errorf("List not ordered by id: %+v", all)
		}
	}

	gibson, err := s.List(ctx, "william gibson") // case-insensitive
	if err != nil {
		t.Fatalf("List filtered: %v", err)
	}
	if len(gibson) != 2 {
		t.Fatalf("List by author: want 2, got %d", len(gibson))
	}
	for _, b := range gibson {
		if b.Author != "William Gibson" {
			t.Errorf("unexpected author in filtered result: %+v", b)
		}
	}

	none, err := s.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List no match: %v", err)
	}
	if len(none) != 0 {
		t.Errorf("want empty list, got %+v", none)
	}
}

func TestDuplicateISBN(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	if _, err := s.Create(ctx, Book{Title: "A", Author: "X", ISBN: "1234567890"}); err != nil {
		t.Fatalf("first Create: %v", err)
	}
	_, err := s.Create(ctx, Book{Title: "B", Author: "Y", ISBN: "1234567890"})
	if !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("want ErrDuplicateISBN, got %v", err)
	}

	// Empty ISBNs must not collide with each other.
	for i := 0; i < 2; i++ {
		if _, err := s.Create(ctx, Book{Title: "C", Author: "Z"}); err != nil {
			t.Errorf("Create without ISBN #%d: %v", i, err)
		}
	}
}
