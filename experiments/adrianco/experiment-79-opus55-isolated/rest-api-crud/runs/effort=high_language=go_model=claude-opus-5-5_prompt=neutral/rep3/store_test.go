package main

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"
)

func openTestStore(t *testing.T, path string) *Store {
	t.Helper()
	store, err := OpenStore(context.Background(), path)
	if err != nil {
		t.Fatalf("open store %q: %v", path, err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func TestStoreCRUD(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, ":memory:")

	created, err := store.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if created.ID <= 0 {
		t.Fatalf("create returned ID %d, want a positive ID", created.ID)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	updated, err := store.Update(ctx, created.ID, Book{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if err != nil {
		t.Fatalf("update: %v", err)
	}
	want := Book{ID: created.ID, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969}
	if updated != want {
		t.Errorf("update = %+v, want %+v", updated, want)
	}
	if got, err := store.Get(ctx, created.ID); err != nil || got != want {
		t.Errorf("get after update = %+v, %v; want %+v", got, err, want)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("get after delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingBook(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, ":memory:")

	if _, err := store.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 42, Book{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreDoesNotReuseIDs(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, ":memory:")

	first, err := store.Create(ctx, Book{Title: "First", Author: "A"})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if err := store.Delete(ctx, first.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	second, err := store.Create(ctx, Book{Title: "Second", Author: "A"})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if second.ID == first.ID {
		t.Errorf("ID %d was reused after its book was deleted", first.ID)
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	// A path containing URI metacharacters must still address a single file.
	path := filepath.Join(t.TempDir(), "my books? #1 100%.db")

	store, err := OpenStore(ctx, path)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	created, err := store.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("close: %v", err)
	}

	reopened := openTestStore(t, path)
	got, err := reopened.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("get after reopen = %+v, want %+v", got, created)
	}
}

func TestStoreConcurrentWrites(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))

	const writers = 20
	var wg sync.WaitGroup
	errs := make(chan error, writers)
	for range writers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := store.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert"})
			errs <- err
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Errorf("concurrent create: %v", err)
		}
	}

	books, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(books) != writers {
		t.Errorf("stored %d books, want %d", len(books), writers)
	}
	seen := map[int64]bool{}
	for _, b := range books {
		if seen[b.ID] {
			t.Errorf("duplicate ID %d", b.ID)
		}
		seen[b.ID] = true
	}
}
