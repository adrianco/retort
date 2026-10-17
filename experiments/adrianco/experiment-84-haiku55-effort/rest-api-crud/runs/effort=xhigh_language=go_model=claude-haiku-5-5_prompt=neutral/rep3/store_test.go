package main

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func openTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return store
}

func TestStoreCRUDRoundTrip(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t)

	// Optional fields left nil must come back as nil, not as zero values.
	created, err := store.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create did not assign an ID")
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != "Dune" || got.Author != "Frank Herbert" || got.Year != nil || got.ISBN != nil {
		t.Errorf("Get returned %+v", got)
	}

	updated, err := store.Update(ctx, created.ID, Book{
		Title:  "Dune Messiah",
		Author: "Frank Herbert",
		Year:   ptr(1969),
		ISBN:   ptr("9780306406157"),
	})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.ID != created.ID || updated.Title != "Dune Messiah" {
		t.Errorf("Update returned %+v", updated)
	}
	got, err = store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after Update: %v", err)
	}
	if got.Year == nil || *got.Year != 1969 || got.ISBN == nil || *got.ISBN != "9780306406157" {
		t.Errorf("Update not persisted: %+v", got)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: got %v, want ErrNotFound", err)
	}
}

func TestStoreMissingRowsReturnNotFound(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t)

	if _, err := store.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: got %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 42, Book{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: got %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: got %v, want ErrNotFound", err)
	}
}

func TestStoreListFiltersByAuthorCaseInsensitively(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t)

	for _, b := range []Book{
		{Title: "A Wizard of Earthsea", Author: "Ursula K. Le Guin"},
		{Title: "The Left Hand of Darkness", Author: "ursula k. le guin"},
		{Title: "Dune", Author: "Frank Herbert"},
	} {
		if _, err := store.Create(ctx, b); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	all, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 3 || all[0].ID > all[1].ID || all[1].ID > all[2].ID {
		t.Errorf("List() = %+v, want 3 books in ID order", all)
	}

	le, err := store.List(ctx, "Ursula K. Le Guin")
	if err != nil {
		t.Fatalf("List(author): %v", err)
	}
	if len(le) != 2 {
		t.Errorf("List(Ursula K. Le Guin) returned %d books, want 2", len(le))
	}

	none, err := store.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List(no match): %v", err)
	}
	if none == nil || len(none) != 0 {
		t.Errorf("List(no match) = %#v, want empty non-nil slice", none)
	}
}

func TestStoreDataPersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "books.db")

	first, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := first.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	second, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer second.Close()
	if _, err := second.Get(ctx, created.ID); err != nil {
		t.Errorf("Get after reopen: %v", err)
	}
}
