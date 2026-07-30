package main

import (
	"context"
	"errors"
	"path/filepath"
	"strconv"
	"sync"
	"testing"
	"time"
)

func itoa(id int64) string { return strconv.FormatInt(id, 10) }

func TestStoreCRUD(t *testing.T) {
	store := OpenTestStore(t)
	ctx := context.Background()

	created, err := store.Create(ctx, dune)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID < 1 {
		t.Fatalf("ID = %d, want positive", created.ID)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Errorf("Get = %+v, want %+v", got, created)
	}

	updated, err := store.Update(ctx, created.ID, BookInput{Title: "Dune", Author: "F. Herbert", Year: 1965})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Author != "F. Herbert" || updated.ISBN != "" {
		t.Errorf("Update = %+v, want author replaced and isbn cleared", updated)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}

	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete error = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, created.ID, dune); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update after Delete error = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete after Delete error = %v, want ErrNotFound", err)
	}
}

// TestStorePersistsAcrossRestart is the point of using SQLite rather than a
// map: data must outlive the process.
func TestStorePersistsAcrossRestart(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	ctx := context.Background()

	first, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := first.Create(ctx, dune)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	second, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen store: %v", err)
	}
	defer second.Close()

	got, err := second.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("after reopen = %+v, want %+v", got, created)
	}
}

func TestStoreListFilterAndOrder(t *testing.T) {
	store := OpenTestStore(t)
	ctx := context.Background()

	for _, in := range []BookInput{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Neuromancer", Author: "William Gibson"},
		{Title: "Dune Messiah", Author: "FRANK HERBERT"},
	} {
		if _, err := store.Create(ctx, in); err != nil {
			t.Fatalf("Create %q: %v", in.Title, err)
		}
	}

	all, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("List returned %d books, want 3", len(all))
	}
	for i := 1; i < len(all); i++ {
		if all[i-1].ID >= all[i].ID {
			t.Errorf("List is not ordered by id: %v", all)
			break
		}
	}

	herbert, err := store.List(ctx, "frank herbert")
	if err != nil {
		t.Fatalf("List(author): %v", err)
	}
	if len(herbert) != 2 {
		t.Errorf("case-insensitive filter returned %d books, want 2", len(herbert))
	}

	none, err := store.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List(missing author): %v", err)
	}
	if none == nil || len(none) != 0 {
		t.Errorf("List(missing author) = %v, want a non-nil empty slice", none)
	}
}

// TestStoreConcurrentWrites guards against SQLITE_BUSY under parallel load.
func TestStoreConcurrentWrites(t *testing.T) {
	store := OpenTestStore(t)
	ctx := context.Background()

	const writers = 16
	var wg sync.WaitGroup
	errs := make(chan error, writers)
	for i := range writers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := store.Create(ctx, BookInput{Title: "Book " + itoa(int64(i)), Author: "Author"}); err != nil {
				errs <- err
			}
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Errorf("concurrent Create: %v", err)
	}

	books, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != writers {
		t.Errorf("stored %d books, want %d", len(books), writers)
	}
}

func TestStoreRejectsUnusableDatabasePath(t *testing.T) {
	// A directory can never be opened as a SQLite database file.
	if _, err := OpenStore(t.TempDir()); err == nil {
		t.Error("OpenStore on a directory succeeded, want an error")
	}
}

func TestValidateISBN(t *testing.T) {
	tests := []struct {
		isbn string
		want bool
	}{
		{"9780441013593", true},
		{"978-0-441-01359-3", true},
		{"978 0 441 01359 3", true},
		{"0441013597", true},
		{"0-441-01359-7", true},
		{"044101359X", true},     // ISBN-10 check digit may be X
		{"044101359x", true},     // ...in either case
		{"978044101359X", false}, // ...but ISBN-13 has no X
		{"044101X597", false},    // X is only valid as the check digit
		{"", false},
		{"12345", false},
		{"97804410135931", false},
		{"not-an-isbn", false},
	}
	for _, tc := range tests {
		if got := validISBN(tc.isbn); got != tc.want {
			t.Errorf("validISBN(%q) = %v, want %v", tc.isbn, got, tc.want)
		}
	}
}

func TestValidateReportsAllFields(t *testing.T) {
	now := time.Date(2026, 7, 29, 0, 0, 0, 0, time.UTC)

	err := BookInput{Year: 1200, ISBN: "nope"}.Validate(now)
	var ve ValidationError
	if !errors.As(err, &ve) {
		t.Fatalf("Validate error = %v, want ValidationError", err)
	}
	for _, field := range []string{"title", "author", "year", "isbn"} {
		if ve[field] == "" {
			t.Errorf("missing %q in %v", field, ve)
		}
	}
	if msg := ve.Error(); msg == "" {
		t.Error("ValidationError.Error() is empty")
	}

	if err := (BookInput{Title: "Dune", Author: "Frank Herbert"}).Validate(now); err != nil {
		t.Errorf("Validate(minimal valid book) = %v, want nil", err)
	}
	// A year within the forward-looking window is accepted.
	if err := (BookInput{Title: "Dune", Author: "F", Year: now.Year() + maxYearSlack}).Validate(now); err != nil {
		t.Errorf("Validate(near-future year) = %v, want nil", err)
	}
}
