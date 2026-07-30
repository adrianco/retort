package main

import (
	"context"
	"errors"
	"path/filepath"
	"strconv"
	"testing"
)

func itoa(id int64) string { return strconv.FormatInt(id, 10) }

func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("close store: %v", err)
		}
	})
	return store
}

func TestStoreCRUD(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	created, err := store.Create(ctx, Book{Title: "T", Author: "A", Year: 2020, ISBN: "9780306406157"})
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
	if got != created {
		t.Errorf("Get returned %+v, want %+v", got, created)
	}

	updated, err := store.Update(ctx, created.ID, Book{Title: "T2", Author: "A2", Year: 2021})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "T2" || updated.ISBN != "" || updated.ID != created.ID {
		t.Errorf("Update returned %+v", updated)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete err = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingRows(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	if _, err := store.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 42, Book{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete err = %v, want ErrNotFound", err)
	}
}

func TestStoreDuplicateISBN(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	if _, err := store.Create(ctx, Book{Title: "A", Author: "X", ISBN: "0306406152"}); err != nil {
		t.Fatalf("first Create: %v", err)
	}
	_, err := store.Create(ctx, Book{Title: "B", Author: "X", ISBN: "0306406152"})
	if !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("err = %v, want ErrDuplicateISBN", err)
	}

	// Updating a book onto another book's ISBN is the same conflict.
	third, err := store.Create(ctx, Book{Title: "C", Author: "X"})
	if err != nil {
		t.Fatalf("Create without ISBN: %v", err)
	}
	if _, err := store.Update(ctx, third.ID, Book{Title: "C", Author: "X", ISBN: "0306406152"}); !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("Update err = %v, want ErrDuplicateISBN", err)
	}
}

// TestStorePersistsAcrossReopen confirms rows really land on disk, which an
// in-memory database cannot demonstrate.
func TestStorePersistsAcrossReopen(t *testing.T) {
	dsn := filepath.Join(t.TempDir(), "books.db")
	ctx := context.Background()

	first, err := OpenStore(dsn)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := first.Create(ctx, Book{Title: "Durable", Author: "Author", Year: 2024})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	// Reopening must find the existing schema and data rather than recreating.
	second, err := OpenStore(dsn)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer second.Close()

	got, err := second.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("got %+v, want %+v", got, created)
	}
}

func TestValidateNormalisesInput(t *testing.T) {
	title, author, isbn := "  Spaced Out  ", "  Ada  ", "978-0-306-40615-7"
	year := 2019

	got, err := BookInput{Title: &title, Author: &author, Year: &year, ISBN: &isbn}.Validate()
	if err != nil {
		t.Fatalf("Validate: %v", err)
	}
	if got.Title != "Spaced Out" {
		t.Errorf("Title = %q, want trimmed", got.Title)
	}
	if got.Author != "Ada" {
		t.Errorf("Author = %q, want trimmed", got.Author)
	}
	if got.ISBN != "9780306406157" {
		t.Errorf("ISBN = %q, want digits only", got.ISBN)
	}
}

func TestValidISBN(t *testing.T) {
	valid := []string{"0306406152", "030640615X", "9780306406157"}
	invalid := []string{"1", "12345678901", "030640615Y", "X306406152", "97803064061578"}

	for _, s := range valid {
		if !validISBN(s) {
			t.Errorf("validISBN(%q) = false, want true", s)
		}
	}
	for _, s := range invalid {
		if validISBN(s) {
			t.Errorf("validISBN(%q) = true, want false", s)
		}
	}
}

// TestValidateYearBoundaries pins the optional-year rule: 0 means unknown.
func TestValidateYearBoundaries(t *testing.T) {
	title, author := "T", "A"
	for _, tc := range []struct {
		year    int
		wantErr bool
	}{{0, false}, {1, false}, {2024, false}, {-5, true}, {90000, true}} {
		y := tc.year
		_, err := BookInput{Title: &title, Author: &author, Year: &y}.Validate()
		if gotErr := err != nil; gotErr != tc.wantErr {
			t.Errorf("year %d: err = %v, wantErr = %v", tc.year, err, tc.wantErr)
		}
		if err != nil && !errors.Is(err, ErrValidation) {
			t.Errorf("year %d: err does not match ErrValidation", tc.year)
		}
	}
}
