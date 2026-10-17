package main

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func openTestStore(t *testing.T, path string) *Store {
	t.Helper()
	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore(%q): %v", path, err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func TestStoreDataSurvivesReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	ctx := context.Background()
	input := BookInput{Title: "The Left Hand of Darkness", Author: "Ursula K. Le Guin", Year: 1969, ISBN: "9780441478125"}

	first := openTestStore(t, path)
	created, err := first.Create(ctx, input)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	second := openTestStore(t, path)
	got, err := second.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("after reopen got %+v, want %+v", got, created)
	}
}

func TestStoreIDsAreNotReusedAfterDelete(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))
	ctx := context.Background()

	first, err := store.Create(ctx, BookInput{Title: "A", Author: "X"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Delete(ctx, first.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	second, err := store.Create(ctx, BookInput{Title: "B", Author: "Y"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if second.ID == first.ID {
		t.Errorf("ID %d was reused after delete", first.ID)
	}
}

func TestStoreMissingBookReturnsErrNotFound(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))
	ctx := context.Background()

	if _, err := store.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 42, BookInput{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreListFiltersAuthorIgnoringCase(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))
	ctx := context.Background()
	for _, in := range []BookInput{
		{Title: "A Wizard of Earthsea", Author: "Ursula K. Le Guin"},
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "The Dispossessed", Author: "ursula k. le guin"},
	} {
		if _, err := store.Create(ctx, in); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	all, err := store.List(ctx, "")
	if err != nil || len(all) != 3 {
		t.Fatalf("List(all) = %d books, err %v; want 3", len(all), err)
	}

	filtered, err := store.List(ctx, "URSULA K. LE GUIN")
	if err != nil {
		t.Fatalf("List(author): %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("List(author) = %d books, want 2", len(filtered))
	}
	if filtered[0].ID > filtered[1].ID {
		t.Errorf("results not ordered by ID: %+v", filtered)
	}

	none, err := store.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List(no match): %v", err)
	}
	if none == nil || len(none) != 0 {
		t.Errorf("List(no match) = %#v, want empty non-nil slice", none)
	}
}
