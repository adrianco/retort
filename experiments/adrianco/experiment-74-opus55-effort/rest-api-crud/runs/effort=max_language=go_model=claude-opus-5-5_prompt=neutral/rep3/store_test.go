package main

import (
	"encoding/json"
	"errors"
	"path/filepath"
	"reflect"
	"testing"
)

// newTestStore opens a store backed by a fresh database file.
func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func ptr[T any](v T) *T { return &v }

// assertEqual fails the test if got and want differ. Both are printed as JSON
// so that pointer fields such as Book.Year show their values.
func assertEqual[T any](t *testing.T, got, want T) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		gotJSON, _ := json.Marshal(got)
		wantJSON, _ := json.Marshal(want)
		t.Errorf("got  %s\nwant %s", gotJSON, wantJSON)
	}
}

func TestStoreCRUD(t *testing.T) {
	store := newTestStore(t)
	ctx := t.Context()

	created, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: "978-0441013593"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID < 1 {
		t.Fatalf("Create assigned ID %d, want a positive ID", created.ID)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	assertEqual(t, got, created)

	updated, err := store.Update(ctx, created.ID, BookInput{Title: "Dune Messiah", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	assertEqual(t, updated, Book{ID: created.ID, Title: "Dune Messiah", Author: "Frank Herbert"})
	got, err = store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after Update: %v", err)
	}
	assertEqual(t, got, updated) // year and ISBN were cleared, stored as NULL and ''

	// Re-saving identical values still counts as a match, not "not found".
	if _, err := store.Update(ctx, created.ID, BookInput{Title: "Dune Messiah", Author: "Frank Herbert"}); err != nil {
		t.Fatalf("Update with unchanged values: %v", err)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, created.ID, BookInput{Title: "x", Author: "y"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update after Delete: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete after Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreDoesNotReuseDeletedIDs(t *testing.T) {
	store := newTestStore(t)
	ctx := t.Context()

	first, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert"})
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Delete(ctx, first.ID); err != nil {
		t.Fatal(err)
	}
	second, err := store.Create(ctx, BookInput{Title: "Emma", Author: "Jane Austen"})
	if err != nil {
		t.Fatal(err)
	}
	if second.ID <= first.ID {
		t.Errorf("new book got ID %d after deleting ID %d; IDs must not be reused", second.ID, first.ID)
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	store, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	created, err := store.Create(t.Context(), BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965)})
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}

	reopened, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	got, err := reopened.Get(t.Context(), created.ID)
	if err != nil {
		t.Fatalf("Get after reopening: %v", err)
	}
	assertEqual(t, got, created)
}

func TestOpenStoreInMemory(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()

	// Every operation must see the same database, whichever pooled
	// connection database/sql would otherwise have picked.
	for range 3 {
		if _, err := store.Create(t.Context(), BookInput{Title: "Dune", Author: "Frank Herbert"}); err != nil {
			t.Fatal(err)
		}
	}
	books, err := store.List(t.Context(), "")
	if err != nil {
		t.Fatal(err)
	}
	if len(books) != 3 {
		t.Errorf("List returned %d books, want 3", len(books))
	}
}

func TestOpenStoreFailsForUnusablePath(t *testing.T) {
	path := filepath.Join(t.TempDir(), "no-such-dir", "books.db")
	if store, err := OpenStore(path); err == nil {
		store.Close()
		t.Fatalf("OpenStore(%q) succeeded, want an error", path)
	}
}
