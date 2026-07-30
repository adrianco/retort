package main

import (
	"errors"
	"path/filepath"
	"testing"
)

func TestStoreCRUD(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	created, err := store.Create(Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "x"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create did not assign an ID")
	}

	got, err := store.Get(created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Errorf("Get = %+v, want %+v", got, created)
	}

	updated, err := store.Update(created.ID, Book{Title: "Dune", Author: "F. Herbert", Year: 1966, ISBN: "y"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Author != "F. Herbert" || updated.ID != created.ID {
		t.Errorf("Update = %+v", updated)
	}

	if err := store.Delete(created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingIDs(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	if _, err := store.Get(1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(1, Book{Title: "t", Author: "a"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

// TestStorePersistsToDisk confirms the data survives closing and reopening the
// file-backed database, i.e. it really is stored in SQLite.
func TestStorePersistsToDisk(t *testing.T) {
	dsn := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(dsn)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := store.Create(Book{Title: "Solaris", Author: "Stanisław Lem", Year: 1961})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened, err := OpenStore(dsn)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer reopened.Close()

	got, err := reopened.Get(created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("got %+v, want %+v", got, created)
	}
}

func TestStoreListEmptyIsNotNil(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	books, err := store.List("")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if books == nil {
		t.Error("List returned nil, want empty slice")
	}
	if len(books) != 0 {
		t.Errorf("List returned %d books, want 0", len(books))
	}
}
