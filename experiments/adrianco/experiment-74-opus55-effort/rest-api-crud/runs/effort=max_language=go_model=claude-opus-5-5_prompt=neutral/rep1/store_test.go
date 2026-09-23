package main

import (
	"errors"
	"fmt"
	"path/filepath"
	"reflect"
	"sync"
	"testing"
)

// openTestStore opens a Store at path that is closed when the test ends.
func openTestStore(t *testing.T, path string) *Store {
	t.Helper()
	store, err := OpenStore(t.Context(), path)
	if err != nil {
		t.Fatalf("OpenStore(%q): %v", path, err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func TestStoreCRUD(t *testing.T) {
	ctx := t.Context()
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))

	created, err := store.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965)})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID < 1 {
		t.Fatalf("Create assigned id %d, want a positive id", created.ID)
	}
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: ptr(1965)}
	if !reflect.DeepEqual(created, want) {
		t.Errorf("Create = %s, want %s", toJSON(created), toJSON(want))
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil || !reflect.DeepEqual(got, want) {
		t.Errorf("Get = %s, %v; want %s, nil", toJSON(got), err, toJSON(want))
	}

	// Update replaces every field: the year is cleared and an ISBN added.
	want = Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", ISBN: ptr("9780441172719")}
	updated, err := store.Update(ctx, want)
	if err != nil || !reflect.DeepEqual(updated, want) {
		t.Errorf("Update = %s, %v; want %s, nil", toJSON(updated), err, toJSON(want))
	}
	if got, err := store.Get(ctx, created.ID); err != nil || !reflect.DeepEqual(got, want) {
		t.Errorf("Get after Update = %s, %v; want %s, nil", toJSON(got), err, toJSON(want))
	}

	for author, wantBooks := range map[string][]Book{
		"":        {want},
		"HERBERT": {want},
		"Asimov":  {},
	} {
		books, err := store.List(ctx, author)
		if err != nil || !reflect.DeepEqual(books, wantBooks) {
			t.Errorf("List(%q) = %s, %v; want %s, nil", author, toJSON(books), err, toJSON(wantBooks))
		}
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, want); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update after Delete: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("second Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreKeepsBooksAcrossRestarts(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(t.Context(), path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	kept, err := store.Create(t.Context(), Book{Title: "Emma", Author: "Jane Austen", Year: ptr(1815)})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	deleted, err := store.Create(t.Context(), Book{Title: "Dune", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Delete(t.Context(), deleted.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened := openTestStore(t, path)
	books, err := reopened.List(t.Context(), "")
	if err != nil || !reflect.DeepEqual(books, []Book{kept}) {
		t.Errorf("List after reopening = %s, %v; want %s, nil", toJSON(books), err, toJSON([]Book{kept}))
	}

	// The newest book was deleted, yet its ID is not handed out again, even
	// after a restart.
	next, err := reopened.Create(t.Context(), Book{Title: "Persuasion", Author: "Jane Austen"})
	if err != nil {
		t.Fatalf("Create after reopening: %v", err)
	}
	if next.ID == deleted.ID {
		t.Errorf("Create after reopening reused id %d of a deleted book", next.ID)
	}
}

func TestStoreInMemoryIsOneDatabase(t *testing.T) {
	// Every connection to ":memory:" would get its own empty database, so this
	// only works if the store never opens more than one.
	store := openTestStore(t, ":memory:")

	const n = 10
	var wg sync.WaitGroup
	for i := range n {
		wg.Go(func() {
			if _, err := store.Create(t.Context(), Book{Title: fmt.Sprintf("Book %d", i), Author: "Anon"}); err != nil {
				t.Errorf("Create: %v", err)
			}
		})
	}
	wg.Wait()

	books, err := store.List(t.Context(), "")
	if err != nil || len(books) != n {
		t.Errorf("List = %d books, %v; want %d books, nil", len(books), err, n)
	}
}

func TestStoreRejectsBooksWithoutTitleOrAuthor(t *testing.T) {
	// The API validates input before it reaches the store; the schema's CHECK
	// constraints are a second line of defence.
	store := openTestStore(t, ":memory:")
	for _, b := range []Book{
		{Title: "", Author: "Frank Herbert"},
		{Title: "Dune", Author: ""},
	} {
		if _, err := store.Create(t.Context(), b); err == nil {
			t.Errorf("Create(%s) succeeded, want an error", toJSON(b))
		}
	}
}
