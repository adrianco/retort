package main

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

// newTestStore opens a fresh database file in a temporary directory.
func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func TestStoreCRUD(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created, err := store.Create(ctx, BookFields{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "0306406152"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create returned zero ID")
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Fatalf("Get = %+v, want %+v", got, created)
	}

	updated, err := store.Update(ctx, created.ID, BookFields{Title: "Dune Messiah", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 0 || updated.ISBN != "" {
		t.Fatalf("Update = %+v, want replaced fields with same ID", updated)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get after delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingBookReturnsNotFound(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	if _, err := store.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 42, BookFields{Title: "x", Author: "y"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreListFiltersByAuthorCaseInsensitively(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	for _, f := range []BookFields{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Children of Dune", Author: "frank herbert"},
	} {
		if _, err := store.Create(ctx, f); err != nil {
			t.Fatalf("Create(%q): %v", f.Title, err)
		}
	}

	all, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("List all: got %d books, want 3", len(all))
	}

	herbert, err := store.List(ctx, "FRANK HERBERT")
	if err != nil {
		t.Fatalf("List by author: %v", err)
	}
	if len(herbert) != 2 || herbert[0].Title != "Dune" || herbert[1].Title != "Children of Dune" {
		t.Fatalf("List by author = %+v, want Dune and Children of Dune in ID order", herbert)
	}

	none, err := store.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List no match: %v", err)
	}
	if none == nil || len(none) != 0 {
		t.Fatalf("List no match = %#v, want empty non-nil slice", none)
	}
}

func TestOpenStoreIsIdempotent(t *testing.T) {
	path := filepath.Join(t.TempDir(), "reopen.db")
	ctx := context.Background()

	first, err := OpenStore(path)
	if err != nil {
		t.Fatalf("first OpenStore: %v", err)
	}
	if _, err := first.Create(ctx, BookFields{Title: "Dune", Author: "Frank Herbert"}); err != nil {
		t.Fatalf("Create: %v", err)
	}
	first.Close()

	second, err := OpenStore(path)
	if err != nil {
		t.Fatalf("second OpenStore: %v", err)
	}
	defer second.Close()

	books, err := second.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != 1 {
		t.Fatalf("after reopen: got %d books, want 1 (data should persist)", len(books))
	}
}
