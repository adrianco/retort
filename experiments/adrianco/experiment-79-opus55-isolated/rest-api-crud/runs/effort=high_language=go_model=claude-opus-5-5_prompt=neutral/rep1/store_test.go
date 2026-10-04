package main

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	// The directory name exercises the characters that are special in a SQLite URI.
	path := filepath.Join(t.TempDir(), "my books #1 100%?", "books.db")
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("database file was not created at the requested path: %v", err)
	}

	store, err = OpenStore(path)
	if err != nil {
		t.Fatalf("reopen OpenStore: %v", err)
	}
	defer store.Close()

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("after reopen got %+v, want %+v", got, created)
	}
}

func TestStoreNotFound(t *testing.T) {
	ctx := context.Background()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	if _, err := store.Get(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get error = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 1, BookInput{Title: "t", Author: "a"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update error = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete error = %v, want ErrNotFound", err)
	}
}

func TestStoreDoesNotReuseDeletedIDs(t *testing.T) {
	ctx := context.Background()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	first, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Delete(ctx, first.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	second, err := store.Create(ctx, BookInput{Title: "Emma", Author: "Jane Austen"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if second.ID == first.ID {
		t.Errorf("new book reused deleted ID %d", first.ID)
	}
}
