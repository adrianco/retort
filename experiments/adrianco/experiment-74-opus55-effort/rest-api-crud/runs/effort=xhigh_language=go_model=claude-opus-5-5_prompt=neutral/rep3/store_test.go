package main

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	st, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { st.Close() })
	return st
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "books.db")

	st, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	year, isbn := 1969, "0306406152"
	created, err := st.Create(ctx, BookInput{Title: "The Left Hand of Darkness", Author: "Ursula K. Le Guin", Year: &year, ISBN: &isbn})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := st.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	st, err = OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer st.Close()
	got, err := st.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got.Title != created.Title || got.Author != created.Author || *got.Year != year || *got.ISBN != isbn ||
		!got.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("book after reopen = %+v, want %+v", got, created)
	}
}

func TestStoreInMemory(t *testing.T) {
	ctx := context.Background()
	st, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer st.Close()
	for _, title := range []string{"A", "B"} {
		if _, err := st.Create(ctx, BookInput{Title: title, Author: "X"}); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}
	books, err := st.List(ctx, ListFilter{})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != 2 {
		t.Errorf("got %d books, want 2", len(books))
	}
}

func TestStoreErrors(t *testing.T) {
	ctx := context.Background()
	st := newTestStore(t)

	if _, err := st.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get missing: err = %v, want ErrNotFound", err)
	}
	if _, err := st.Update(ctx, 42, BookInput{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update missing: err = %v, want ErrNotFound", err)
	}
	if err := st.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete missing: err = %v, want ErrNotFound", err)
	}

	isbn := "9780306406157"
	if _, err := st.Create(ctx, BookInput{Title: "One", Author: "A", ISBN: &isbn}); err != nil {
		t.Fatalf("Create: %v", err)
	}
	if _, err := st.Create(ctx, BookInput{Title: "Two", Author: "B", ISBN: &isbn}); !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("duplicate ISBN: err = %v, want ErrDuplicateISBN", err)
	}
	// Books without an ISBN never conflict with each other.
	for range 2 {
		if _, err := st.Create(ctx, BookInput{Title: "No ISBN", Author: "C"}); err != nil {
			t.Errorf("Create without ISBN: %v", err)
		}
	}
}

func TestStoreListAuthorFilterIsLiteral(t *testing.T) {
	ctx := context.Background()
	st := newTestStore(t)
	for _, author := range []string{"Ann_Smith", "AnnXSmith", "100% Pure", `Back\slash`} {
		if _, err := st.Create(ctx, BookInput{Title: "T", Author: author}); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}
	tests := map[string]int{
		"_":        1, // matches only the literal underscore, not any character
		"n_s":      1,
		"%":        1,
		"0% p":     1,
		`\`:        1,
		`k\s`:      1,
		"ANN":      2,
		"smith":    2,
		"no-match": 0,
	}
	for filter, want := range tests {
		books, err := st.List(ctx, ListFilter{Author: filter})
		if err != nil {
			t.Fatalf("List(%q): %v", filter, err)
		}
		if len(books) != want {
			t.Errorf("List(author=%q) returned %d books, want %d", filter, len(books), want)
		}
	}
}
