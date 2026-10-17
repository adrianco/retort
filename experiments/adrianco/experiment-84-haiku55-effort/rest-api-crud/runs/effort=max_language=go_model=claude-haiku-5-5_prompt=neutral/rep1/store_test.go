package main

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"reflect"
	"slices"
	"sync"
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

func TestStoreCreateAndGet(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created, err := store.Create(ctx, Book{
		Title:  "Dune",
		Author: "Frank Herbert",
		Year:   intPtr(1965),
		ISBN:   strPtr("9780441172719"),
	})
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
	if !reflect.DeepEqual(got, created) {
		t.Fatalf("Get = %+v, want %+v", got, created)
	}

	// Unset optional fields are stored as NULL and read back as nil, not as zero values.
	sparse, err := store.Create(ctx, Book{Title: "Anonymous", Author: "Unknown"})
	if err != nil {
		t.Fatalf("Create sparse: %v", err)
	}
	got, err = store.Get(ctx, sparse.ID)
	if err != nil {
		t.Fatalf("Get sparse: %v", err)
	}
	if got.Year != nil || got.ISBN != nil {
		t.Fatalf("unset fields = year %v, isbn %v; want both nil", got.Year, got.ISBN)
	}
}

func TestStoreUpdateAndDelete(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created, err := store.Create(ctx, Book{Title: "Old", Author: "Old", Year: intPtr(1900)})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	// Update replaces every field, so an unset Year is cleared.
	updated, err := store.Update(ctx, created.ID, Book{Title: "New", Author: "Author"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.ID != created.ID || updated.Title != "New" || updated.Year != nil {
		t.Fatalf("Update returned %+v", updated)
	}
	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after update: %v", err)
	}
	if !reflect.DeepEqual(got, updated) {
		t.Fatalf("stored %+v, want %+v", got, updated)
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

	if _, err := store.Get(ctx, 999); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 999, Book{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 999); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreDoesNotReuseIDs(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	first, err := store.Create(ctx, Book{Title: "First", Author: "A"})
	if err != nil {
		t.Fatalf("Create first: %v", err)
	}
	if err := store.Delete(ctx, first.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	second, err := store.Create(ctx, Book{Title: "Second", Author: "B"})
	if err != nil {
		t.Fatalf("Create second: %v", err)
	}
	if second.ID <= first.ID {
		t.Fatalf("second ID = %d after deleting %d; a deleted ID must not be reused", second.ID, first.ID)
	}
}

func TestStoreListFiltersByAuthor(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	for _, b := range []Book{
		{Title: "Nineteen Eighty-Four", Author: "George Orwell"},
		{Title: "The Left Hand of Darkness", Author: "Ursula K. Le Guin"},
		{Title: "100 Percent", Author: "100% Author"},
		{Title: "Snake Case", Author: "under_score"},
		{Title: "Animal Farm", Author: "George Orwell"},
	} {
		if _, err := store.Create(ctx, b); err != nil {
			t.Fatalf("Create %q: %v", b.Title, err)
		}
	}

	allTitles := []string{"Nineteen Eighty-Four", "The Left Hand of Darkness", "100 Percent", "Snake Case", "Animal Farm"}
	tests := []struct {
		name   string
		author string
		want   []string
	}{
		{name: "no filter returns everything in ID order", author: "", want: allTitles},
		{name: "substring match", author: "Orwell", want: []string{"Nineteen Eighty-Four", "Animal Farm"}},
		{name: "case-insensitive", author: "LE GUIN", want: []string{"The Left Hand of Darkness"}},
		{name: "percent sign is literal, not a wildcard", author: "%", want: []string{"100 Percent"}},
		{name: "underscore is literal, not a wildcard", author: "_", want: []string{"Snake Case"}},
		{name: "no match", author: "nobody", want: nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			books, err := store.List(ctx, tt.author)
			if err != nil {
				t.Fatalf("List(%q): %v", tt.author, err)
			}
			var titles []string
			for _, b := range books {
				titles = append(titles, b.Title)
			}
			if !slices.Equal(titles, tt.want) {
				t.Fatalf("List(%q) titles = %v, want %v", tt.author, titles, tt.want)
			}
		})
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := store.Create(ctx, Book{Title: "Persisted", Author: "A", Year: intPtr(2001)})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer reopened.Close()
	got, err := reopened.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if !reflect.DeepEqual(got, created) {
		t.Fatalf("after reopen = %+v, want %+v", got, created)
	}
}

func TestStoreHandlesConcurrentWrites(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	const writers = 20
	var wg sync.WaitGroup
	errs := make(chan error, writers)
	for i := range writers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := store.Create(ctx, Book{Title: fmt.Sprintf("Book %d", i), Author: "A"})
			errs <- err
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Errorf("concurrent Create: %v", err)
		}
	}

	books, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != writers {
		t.Fatalf("stored %d books, want %d", len(books), writers)
	}
}
