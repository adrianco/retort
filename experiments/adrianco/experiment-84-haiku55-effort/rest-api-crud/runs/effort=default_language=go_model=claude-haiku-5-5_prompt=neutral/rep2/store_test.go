package main

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func TestStoreCRUD(t *testing.T) {
	ctx := context.Background()
	s := newTestStore(t)

	created, err := s.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create returned zero ID")
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Errorf("Get = %+v, want %+v", got, created)
	}

	updated, err := s.Update(ctx, created.ID, BookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "Dune Messiah" || updated.ISBN != "" {
		t.Errorf("Update returned %+v", updated)
	}
	got, _ = s.Get(ctx, created.ID)
	if got != updated {
		t.Errorf("after Update, Get = %+v, want %+v", got, updated)
	}

	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingBook(t *testing.T) {
	ctx := context.Background()
	s := newTestStore(t)
	in := BookInput{Title: "Dune", Author: "Frank Herbert"}

	if _, err := s.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := s.Update(ctx, 42, in); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreListFiltersByAuthor(t *testing.T) {
	ctx := context.Background()
	s := newTestStore(t)

	if books, err := s.List(ctx, ""); err != nil || books == nil || len(books) != 0 {
		t.Fatalf("empty List = %v, %v; want non-nil empty slice", books, err)
	}

	for _, in := range []BookInput{
		{Title: "The Left Hand of Darkness", Author: "Ursula K. Le Guin"},
		{Title: "The Dispossessed", Author: "Ursula K. Le Guin"},
		{Title: "Dune", Author: "Frank Herbert"},
	} {
		if _, err := s.Create(ctx, in); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	all, err := s.List(ctx, "")
	if err != nil || len(all) != 3 {
		t.Fatalf("List all = %d books, err %v; want 3", len(all), err)
	}
	if all[0].Title != "The Left Hand of Darkness" {
		t.Errorf("List not ordered by ID: first = %q", all[0].Title)
	}

	guin, err := s.List(ctx, "ursula k. le guin")
	if err != nil || len(guin) != 2 {
		t.Fatalf("List by author (case-insensitive) = %d books, err %v; want 2", len(guin), err)
	}

	none, err := s.List(ctx, "Nobody")
	if err != nil || none == nil || len(none) != 0 {
		t.Errorf("List unmatched author = %v, %v; want empty non-nil slice", none, err)
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "books.db")

	s, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := s.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	s, err = OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer s.Close()
	got, err := s.Get(ctx, created.ID)
	if err != nil || got.Title != "Dune" {
		t.Errorf("after reopen Get = %+v, %v", got, err)
	}
}
