package main

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func mustCreate(t *testing.T, s *Store, b Book) Book {
	t.Helper()
	created, err := s.Create(context.Background(), b)
	if err != nil {
		t.Fatalf("Create(%+v): %v", b, err)
	}
	return created
}

func TestStoreCRUD(t *testing.T) {
	ctx := context.Background()
	s := newTestStore(t)

	created := mustCreate(t, s, Book{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("9780441172719")})
	if created.ID == 0 {
		t.Fatal("Create returned zero ID")
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != "Dune" || got.Author != "Frank Herbert" || *got.Year != 1965 || *got.ISBN != "9780441172719" {
		t.Errorf("Get = %+v, want stored fields", got)
	}

	// Update replaces all fields, including clearing optional ones.
	updated, err := s.Update(ctx, created.ID, Book{Title: "Dune Messiah", Author: "Frank Herbert"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != nil || updated.ISBN != nil {
		t.Errorf("Update = %+v, want replaced fields with nil year/isbn", updated)
	}

	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreNotFound(t *testing.T) {
	ctx := context.Background()
	s := newTestStore(t)

	if _, err := s.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := s.Update(ctx, 42, Book{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreIDsAreNotReused(t *testing.T) {
	ctx := context.Background()
	s := newTestStore(t)

	first := mustCreate(t, s, Book{Title: "A", Author: "X"})
	if err := s.Delete(ctx, first.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	second := mustCreate(t, s, Book{Title: "B", Author: "X"})
	if second.ID == first.ID {
		t.Errorf("deleted ID %d was reused", first.ID)
	}
}

func TestStoreListAuthorFilter(t *testing.T) {
	ctx := context.Background()
	s := newTestStore(t)

	mustCreate(t, s, Book{Title: "Dune", Author: "Frank Herbert"})
	mustCreate(t, s, Book{Title: "Emma", Author: "Jane Austen"})
	mustCreate(t, s, Book{Title: "Persuasion", Author: "Jane Austen"})
	mustCreate(t, s, Book{Title: "Odd", Author: "100% Real_Author"})

	tests := []struct {
		author string
		want   []string
	}{
		{"", []string{"Dune", "Emma", "Persuasion", "Odd"}},
		{"Jane Austen", []string{"Emma", "Persuasion"}},
		{"austen", []string{"Emma", "Persuasion"}}, // case-insensitive substring
		{"Tolkien", nil},
		{"%", []string{"Odd"}}, // LIKE wildcards are matched literally
		{"l_a", []string{"Odd"}},
		{"_", []string{"Odd"}},
	}
	for _, tc := range tests {
		books, err := s.List(ctx, tc.author)
		if err != nil {
			t.Fatalf("List(%q): %v", tc.author, err)
		}
		if books == nil {
			t.Fatalf("List(%q) returned nil slice; want non-nil for JSON []", tc.author)
		}
		var titles []string
		for _, b := range books {
			titles = append(titles, b.Title)
		}
		if len(titles) != len(tc.want) {
			t.Errorf("List(%q) = %v, want %v", tc.author, titles, tc.want)
			continue
		}
		for i := range titles {
			if titles[i] != tc.want[i] {
				t.Errorf("List(%q) = %v, want %v", tc.author, titles, tc.want)
				break
			}
		}
	}
}

func TestStorePersistsToFile(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "books.db")

	s, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created := mustCreate(t, s, Book{Title: "Dune", Author: "Frank Herbert"})
	if err := s.Close(); err != nil {
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
	if got.Title != "Dune" {
		t.Errorf("Title after reopen = %q, want Dune", got.Title)
	}
}
