package store

import (
	"context"
	"errors"
	"path/filepath"
	"testing"

	"bookservice/internal/book"
)

func openTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := Open(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("Open() error = %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func mustCreate(t *testing.T, s *Store, b book.Book) book.Book {
	t.Helper()
	if err := s.Create(context.Background(), &b); err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	return b
}

func TestCreateAndGet(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	in := book.Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780306406157"}
	created := mustCreate(t, s, in)
	if created.ID == 0 {
		t.Fatal("Create() did not assign an ID")
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get() error = %v", err)
	}
	if got != created {
		t.Errorf("Get() = %+v, want %+v", got, created)
	}
}

func TestGetMissing(t *testing.T) {
	s := openTestStore(t)
	if _, err := s.Get(context.Background(), 42); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get() error = %v, want ErrNotFound", err)
	}
}

func TestListOrderAndAuthorFilter(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	mustCreate(t, s, book.Book{Title: "Dune", Author: "Frank Herbert"})
	mustCreate(t, s, book.Book{Title: "Emma", Author: "Jane Austen"})
	mustCreate(t, s, book.Book{Title: "Children of Dune", Author: "frank herbert"})

	all, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List() error = %v", err)
	}
	if len(all) != 3 || all[0].Title != "Dune" || all[2].Title != "Children of Dune" {
		t.Fatalf("List() = %+v, want 3 books in insertion order", all)
	}

	herbert, err := s.List(ctx, "FRANK HERBERT")
	if err != nil {
		t.Fatalf("List(author) error = %v", err)
	}
	if len(herbert) != 2 {
		t.Fatalf("List(author) returned %d books, want 2: %+v", len(herbert), herbert)
	}
	for _, b := range herbert {
		if b.Author != "Frank Herbert" && b.Author != "frank herbert" {
			t.Errorf("unexpected author in filtered result: %q", b.Author)
		}
	}

	none, err := s.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List(no match) error = %v", err)
	}
	if none == nil || len(none) != 0 {
		t.Errorf("List(no match) = %#v, want non-nil empty slice", none)
	}
}

func TestUpdate(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, s, book.Book{Title: "Dun", Author: "Herbert"})

	updated := book.Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965}
	if err := s.Update(ctx, updated); err != nil {
		t.Fatalf("Update() error = %v", err)
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get() error = %v", err)
	}
	if got != updated {
		t.Errorf("after Update, Get() = %+v, want %+v", got, updated)
	}
}

func TestUpdateMissing(t *testing.T) {
	s := openTestStore(t)
	err := s.Update(context.Background(), book.Book{ID: 99, Title: "T", Author: "A"})
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("Update() error = %v, want ErrNotFound", err)
	}
}

func TestDelete(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, s, book.Book{Title: "Dune", Author: "Frank Herbert"})
	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete() error = %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get() after Delete error = %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("second Delete() error = %v, want ErrNotFound", err)
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	ctx := context.Background()

	s, err := Open(path)
	if err != nil {
		t.Fatalf("Open() error = %v", err)
	}
	created := mustCreate(t, s, book.Book{Title: "Dune", Author: "Frank Herbert"})
	if err := s.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}

	s, err = Open(path)
	if err != nil {
		t.Fatalf("reopen error = %v", err)
	}
	defer s.Close()
	if _, err := s.Get(ctx, created.ID); err != nil {
		t.Fatalf("Get() after reopen error = %v", err)
	}
}
