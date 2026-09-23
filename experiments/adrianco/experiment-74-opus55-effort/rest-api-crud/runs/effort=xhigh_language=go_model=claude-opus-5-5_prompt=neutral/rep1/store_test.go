package main

import (
	"context"
	"errors"
	"path/filepath"
	"slices"
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

func TestStoreCRUD(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID < 1 || created.CreatedAt.IsZero() || !created.CreatedAt.Equal(created.UpdatedAt) {
		t.Fatalf("Create returned unexpected book: %+v", created)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if !sameBook(got, created) {
		t.Fatalf("Get = %+v, want %+v (values must round-trip through the database)", got, created)
	}

	updated, err := store.Update(ctx, created.ID, BookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "" {
		t.Errorf("Update did not replace fields: %+v", updated)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("Update changed created_at: %v -> %v", created.CreatedAt, updated.CreatedAt)
	}
	if updated.UpdatedAt.Before(created.UpdatedAt) {
		t.Errorf("updated_at went backwards: %v -> %v", created.UpdatedAt, updated.UpdatedAt)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get after Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreNotFound(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	if _, err := store.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 42, BookInput{Title: "t", Author: "a"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreListFiltersByAuthor(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	books, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if books == nil || len(books) != 0 {
		t.Fatalf("List on empty store = %#v, want non-nil empty slice", books)
	}

	for _, in := range []BookInput{
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Persuasion", Author: "Jane Austen"},
		{Title: "Sanditon", Author: "Jane Austen Society"}, // must not match an exact filter
	} {
		if _, err := store.Create(ctx, in); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	tests := []struct {
		author string
		want   []string
	}{
		{"", []string{"Emma", "Dune", "Persuasion", "Sanditon"}},
		{"Jane Austen", []string{"Emma", "Persuasion"}},
		{"jane austen", []string{"Emma", "Persuasion"}},
		{"Nobody", nil},
	}
	for _, tc := range tests {
		books, err := store.List(ctx, tc.author)
		if err != nil {
			t.Fatalf("List(%q): %v", tc.author, err)
		}
		if titles := titlesOf(books); !slices.Equal(titles, tc.want) {
			t.Errorf("List(%q) titles = %v, want %v", tc.author, titles, tc.want)
		}
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert"})
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
	if !sameBook(got, created) {
		t.Fatalf("Get after reopen = %+v, want %+v", got, created)
	}
}

func TestStoreDoesNotReuseDeletedIDs(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	// Without AUTOINCREMENT, SQLite would hand out max(id)+1 again, i.e. reuse
	// the ID of the just-deleted (and only) row.
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
		t.Fatalf("new book reused deleted ID %d", first.ID)
	}
}

func TestStoreInMemory(t *testing.T) {
	ctx := context.Background()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore(:memory:): %v", err)
	}
	defer store.Close()

	created, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	// Several sequential calls must all see the same in-memory database.
	for range 3 {
		if _, err := store.Get(ctx, created.ID); err != nil {
			t.Fatalf("Get: %v", err)
		}
	}
}

func titlesOf(books []Book) []string {
	var titles []string
	for _, b := range books {
		titles = append(titles, b.Title)
	}
	return titles
}

// sameBook compares books using time.Equal, since == on time.Time also compares
// location pointers and monotonic readings.
func sameBook(a, b Book) bool {
	return a.ID == b.ID && a.Title == b.Title && a.Author == b.Author && a.Year == b.Year &&
		a.ISBN == b.ISBN && a.CreatedAt.Equal(b.CreatedAt) && a.UpdatedAt.Equal(b.UpdatedAt)
}
