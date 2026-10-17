package main

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"reflect"
	"sync"
	"testing"
)

// openTestStore opens a store at path and closes it when the test ends.
func openTestStore(t *testing.T, path string) *Store {
	t.Helper()
	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore(%q): %v", path, err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return store
}

// newTestStore returns a store backed by a fresh database file.
func newTestStore(t *testing.T) *Store {
	t.Helper()
	return openTestStore(t, filepath.Join(t.TempDir(), "books.db"))
}

// mustCreate stores b and fails the test on error.
func mustCreate(t *testing.T, store *Store, b Book) Book {
	t.Helper()
	created, err := store.Create(context.Background(), b)
	if err != nil {
		t.Fatalf("Create(%s): %v", toJSON(b), err)
	}
	return created
}

// assertBook fails the test unless got and want hold the same data.
func assertBook(t *testing.T, got, want Book) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Errorf("book = %s, want %s", toJSON(got), toJSON(want))
	}
}

func TestStoreCreateAndGet(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, store, Book{
		Title:  "Dune",
		Author: "Frank Herbert",
		Year:   intPtr(1965),
		ISBN:   strPtr("978-0441172719"),
	})
	if created.ID == 0 {
		t.Fatal("Create() returned ID 0")
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get(%d): %v", created.ID, err)
	}
	assertBook(t, got, created)
}

func TestStoreOptionalFieldsRoundTripAsNil(t *testing.T) {
	store := newTestStore(t)

	created := mustCreate(t, store, Book{Title: "Untitled Draft", Author: "Anonymous"})

	got, err := store.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatalf("Get(%d): %v", created.ID, err)
	}
	if got.Year != nil || got.ISBN != nil {
		t.Errorf("book = %s; want year and isbn to be null", toJSON(got))
	}
}

func TestStoreGetMissingBook(t *testing.T) {
	store := newTestStore(t)

	_, err := store.Get(context.Background(), 42)
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get(42) error = %v; want ErrNotFound", err)
	}
}

func TestStoreListOrderAndAuthorFilter(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	dune := mustCreate(t, store, Book{Title: "Dune", Author: "Frank Herbert"})
	neuromancer := mustCreate(t, store, Book{Title: "Neuromancer", Author: "William Gibson"})
	children := mustCreate(t, store, Book{Title: "Children of Dune", Author: "Frank Herbert"})

	tests := []struct {
		name   string
		author string
		want   []Book
	}{
		{name: "no filter returns all books in ID order", author: "", want: []Book{dune, neuromancer, children}},
		{name: "exact author", author: "Frank Herbert", want: []Book{dune, children}},
		{name: "case-insensitive", author: "frank HERBERT", want: []Book{dune, children}},
		{name: "substring", author: "herb", want: []Book{dune, children}},
		{name: "no match returns empty list", author: "Asimov", want: []Book{}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := store.List(ctx, tt.author)
			if err != nil {
				t.Fatalf("List(%q): %v", tt.author, err)
			}
			if got == nil {
				t.Fatal("List() returned nil; want a non-nil slice")
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("List(%q) = %s, want %s", tt.author, toJSON(got), toJSON(tt.want))
			}
		})
	}
}

func TestStoreListTreatsWildcardsLiterally(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	percent := mustCreate(t, store, Book{Title: "Discount Tables", Author: "50% Press"})
	backslash := mustCreate(t, store, Book{Title: "Paths", Author: `Ann\Lee`})
	mustCreate(t, store, Book{Title: "Plain", Author: "Jane Smith"})

	tests := []struct {
		filter  string
		wantIDs []int64
	}{
		{filter: "%", wantIDs: []int64{percent.ID}},
		{filter: "50%", wantIDs: []int64{percent.ID}},
		{filter: "_", wantIDs: nil}, // no author contains a literal underscore
		{filter: `\`, wantIDs: []int64{backslash.ID}},
	}

	for _, tt := range tests {
		got, err := store.List(ctx, tt.filter)
		if err != nil {
			t.Fatalf("List(%q): %v", tt.filter, err)
		}
		var gotIDs []int64
		for _, b := range got {
			gotIDs = append(gotIDs, b.ID)
		}
		if !reflect.DeepEqual(gotIDs, tt.wantIDs) {
			t.Errorf("List(%q) IDs = %v, want %v", tt.filter, gotIDs, tt.wantIDs)
		}
	}
}

func TestStoreUpdate(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, store, Book{
		Title:  "Dune",
		Author: "Frank Herbert",
		Year:   intPtr(1965),
		ISBN:   strPtr("978-0441172719"),
	})

	// Replacing with nil optional fields must clear them in the database.
	updated, err := store.Update(ctx, created.ID, Book{Title: "Dune (Revised)", Author: "F. Herbert"})
	if err != nil {
		t.Fatalf("Update(%d): %v", created.ID, err)
	}
	want := Book{ID: created.ID, Title: "Dune (Revised)", Author: "F. Herbert"}
	assertBook(t, updated, want)

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get(%d) after update: %v", created.ID, err)
	}
	assertBook(t, got, want)
}

func TestStoreUpdateMissingBook(t *testing.T) {
	store := newTestStore(t)

	_, err := store.Update(context.Background(), 7, Book{Title: "Dune", Author: "Frank Herbert"})
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("Update(7) error = %v; want ErrNotFound", err)
	}
}

func TestStoreDelete(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, store, Book{Title: "Dune", Author: "Frank Herbert"})

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete(%d): %v", created.ID, err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete error = %v; want ErrNotFound", err)
	}
	if err := store.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("second Delete error = %v; want ErrNotFound", err)
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	first, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore(first): %v", err)
	}
	created := mustCreate(t, first, Book{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965)})
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	second := openTestStore(t, path)
	got, err := second.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatalf("Get(%d) after reopen: %v", created.ID, err)
	}
	assertBook(t, got, created)
}

func TestStoreConcurrentWrites(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	const writers = 20
	var wg sync.WaitGroup
	errs := make(chan error, writers)
	for i := range writers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := store.Create(ctx, Book{Title: fmt.Sprintf("Book %d", i), Author: "Concurrent"})
			errs <- err
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Fatalf("concurrent Create: %v", err)
		}
	}

	books, err := store.List(ctx, "Concurrent")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != writers {
		t.Errorf("stored %d books, want %d", len(books), writers)
	}
}

func TestStorePingFailsAfterClose(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))
	ctx := context.Background()

	if err := store.Ping(ctx); err != nil {
		t.Fatalf("Ping() on open store: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	if err := store.Ping(ctx); err == nil {
		t.Error("Ping() on closed store succeeded; want an error")
	}
}
