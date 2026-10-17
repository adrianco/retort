package bookapi

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

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

	created, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create returned zero ID")
	}
	if created.Title != "Dune" || created.Author != "Frank Herbert" || created.Year != 1965 || created.ISBN != "9780441172719" {
		t.Fatalf("Create returned %+v", created)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Fatalf("Get = %+v, want %+v", got, created)
	}

	updated, err := store.Update(ctx, created.ID, BookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "" {
		t.Fatalf("Update returned %+v", updated)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get after delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingBook(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	if _, err := store.Get(ctx, 999); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 999, BookInput{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 999); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreListFiltersByAuthor(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	// Empty collection lists as an empty slice, not nil.
	books, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if books == nil || len(books) != 0 {
		t.Fatalf("List on empty store = %#v, want empty non-nil slice", books)
	}

	for _, in := range []BookInput{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Children of Dune", Author: "Frank Herbert"},
	} {
		if _, err := store.Create(ctx, in); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	all, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List all: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("List all returned %d books, want 3", len(all))
	}
	if all[0].Title != "Dune" || all[2].Title != "Children of Dune" {
		t.Errorf("List all not ordered by id: %+v", all)
	}

	herbert, err := store.List(ctx, "frank herbert")
	if err != nil {
		t.Fatalf("List by author: %v", err)
	}
	if len(herbert) != 2 {
		t.Fatalf("List by author returned %d books, want 2", len(herbert))
	}
	for _, b := range herbert {
		if b.Author != "Frank Herbert" {
			t.Errorf("filtered result has author %q", b.Author)
		}
	}

	none, err := store.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List no match: %v", err)
	}
	if none == nil || len(none) != 0 {
		t.Errorf("List no match = %#v, want empty non-nil slice", none)
	}
}
