package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"reflect"
	"sync"
	"testing"
)

// newTestStore opens a store on a new database file that is deleted after
// the test.
func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(t.Context(), filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

// mustCreate adds a book to store, failing the test if that fails.
func mustCreate(t *testing.T, store *Store, in BookInput) Book {
	t.Helper()
	book, err := store.CreateBook(t.Context(), in)
	if err != nil {
		t.Fatalf("CreateBook(%q): %v", in.Title, err)
	}
	return book
}

// assertEqual fails the test unless got and want are deeply equal. They are
// printed as JSON, which shows the values behind pointer fields.
func assertEqual[T any](t *testing.T, got, want T) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		gotJSON, _ := json.Marshal(got)
		wantJSON, _ := json.Marshal(want)
		t.Errorf("got  %s\nwant %s", gotJSON, wantJSON)
	}
}

func TestStoreCRUD(t *testing.T) {
	ctx := t.Context()
	store := newTestStore(t)

	created := mustCreate(t, store, BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("978-0441172719")})
	want := Book{ID: 1, Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("978-0441172719")}
	assertEqual(t, created, want)

	got, err := store.GetBook(ctx, created.ID)
	if err != nil {
		t.Fatalf("GetBook: %v", err)
	}
	assertEqual(t, got, want)

	// An update replaces the whole book, so omitted optional fields are cleared.
	updated, err := store.UpdateBook(ctx, created.ID, BookInput{Title: "Dune Messiah", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("UpdateBook: %v", err)
	}
	want = Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert"}
	assertEqual(t, updated, want)
	got, err = store.GetBook(ctx, created.ID)
	if err != nil {
		t.Fatalf("GetBook after update: %v", err)
	}
	assertEqual(t, got, want)

	if err := store.DeleteBook(ctx, created.ID); err != nil {
		t.Fatalf("DeleteBook: %v", err)
	}
	if _, err := store.GetBook(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("GetBook after delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingBook(t *testing.T) {
	ctx := t.Context()
	store := newTestStore(t)

	if _, err := store.GetBook(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("GetBook: err = %v, want ErrNotFound", err)
	}
	if _, err := store.UpdateBook(ctx, 42, BookInput{Title: "Dune", Author: "Frank Herbert"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("UpdateBook: err = %v, want ErrNotFound", err)
	}
	if err := store.DeleteBook(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("DeleteBook: err = %v, want ErrNotFound", err)
	}
}

func TestStoreListBooks(t *testing.T) {
	store := newTestStore(t)
	books := []Book{
		mustCreate(t, store, BookInput{Title: "Nineteen Eighty-Four", Author: "George Orwell"}),
		mustCreate(t, store, BookInput{Title: "Brave New World", Author: "Aldous Huxley"}),
		mustCreate(t, store, BookInput{Title: "Animal Farm", Author: "George Orwell"}),
	}

	tests := []struct {
		author string
		want   []Book
	}{
		{"", books},
		{"George Orwell", []Book{books[0], books[2]}},
		{"orwell", []Book{books[0], books[2]}},
		{"HUXLEY", []Book{books[1]}},
		{"Tolkien", []Book{}},
		// LIKE wildcards have no special meaning.
		{"%", []Book{}},
		{"_", []Book{}},
	}
	for _, tt := range tests {
		t.Run(fmt.Sprintf("author=%q", tt.author), func(t *testing.T) {
			got, err := store.ListBooks(t.Context(), tt.author)
			if err != nil {
				t.Fatalf("ListBooks: %v", err)
			}
			assertEqual(t, got, tt.want)
		})
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := t.Context()
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(ctx, path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created := mustCreate(t, store, BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965)})
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened, err := OpenStore(ctx, path)
	if err != nil {
		t.Fatalf("OpenStore again: %v", err)
	}
	defer reopened.Close()
	got, err := reopened.GetBook(ctx, created.ID)
	if err != nil {
		t.Fatalf("GetBook after reopening: %v", err)
	}
	assertEqual(t, got, created)
}

func TestStoreDoesNotReuseIDs(t *testing.T) {
	store := newTestStore(t)
	in := BookInput{Title: "Dune", Author: "Frank Herbert"}
	mustCreate(t, store, in)
	second := mustCreate(t, store, in)
	if err := store.DeleteBook(t.Context(), second.ID); err != nil {
		t.Fatalf("DeleteBook: %v", err)
	}
	if third := mustCreate(t, store, in); third.ID <= second.ID {
		t.Errorf("new book got ID %d after ID %d was deleted; IDs must not be reused", third.ID, second.ID)
	}
}

// The HTTP server calls the store from many goroutines at once.
func TestStoreConcurrentWrites(t *testing.T) {
	tests := []struct{ name, path string }{
		{"file", filepath.Join(t.TempDir(), "books.db")},
		{"memory", ":memory:"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			store, err := OpenStore(t.Context(), tt.path)
			if err != nil {
				t.Fatalf("OpenStore: %v", err)
			}
			defer store.Close()

			const writers = 20
			var wg sync.WaitGroup
			for i := range writers {
				wg.Go(func() {
					in := BookInput{Title: fmt.Sprintf("Book %d", i), Author: "Anonymous"}
					if _, err := store.CreateBook(t.Context(), in); err != nil {
						t.Errorf("CreateBook: %v", err)
					}
				})
			}
			wg.Wait()

			books, err := store.ListBooks(t.Context(), "")
			if err != nil {
				t.Fatalf("ListBooks: %v", err)
			}
			if len(books) != writers {
				t.Errorf("stored %d books, want %d", len(books), writers)
			}
		})
	}
}
