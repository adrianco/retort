package main

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"path/filepath"
	"testing"
	"time"
)

func discardLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(context.Background(), filepath.Join(t.TempDir(), "store.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return store
}

func TestStoreCRUD(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created, err := store.Create(ctx, BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Errorf("Get = %+v, want %+v", got, created)
	}

	updated, err := store.Update(ctx, created.ID, BookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "" {
		t.Errorf("Update = %+v, want the replaced fields", updated)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("CreatedAt = %v, want it preserved at %v", updated.CreatedAt, created.CreatedAt)
	}

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingRows(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	if _, err := store.Get(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 1, BookInput{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete = %v, want ErrNotFound", err)
	}
}

func TestStoreDuplicateISBN(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	if _, err := store.Create(ctx, BookInput{Title: "A", Author: "A", ISBN: "9780441013593"}); err != nil {
		t.Fatalf("Create: %v", err)
	}
	if _, err := store.Create(ctx, BookInput{Title: "B", Author: "B", ISBN: "9780441013593"}); !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("duplicate Create = %v, want ErrDuplicateISBN", err)
	}

	// Books without an ISBN store NULL, which SQLite treats as distinct.
	for range 3 {
		if _, err := store.Create(ctx, BookInput{Title: "No ISBN", Author: "A"}); err != nil {
			t.Fatalf("Create without isbn: %v", err)
		}
	}
	books, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != 4 {
		t.Errorf("List returned %d books, want 4", len(books))
	}
}

// TestStorePersistsAcrossReopen confirms rows really land on disk rather than
// living only in the process.
func TestStorePersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "persist.db")

	store, err := OpenStore(ctx, path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := store.Create(ctx, BookInput{Title: "Persisted", Author: "A", Year: 2001})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened, err := OpenStore(ctx, path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer reopened.Close()

	got, err := reopened.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("after reopen = %+v, want %+v", got, created)
	}
}

// TestStoreTimestampsUseInjectedClock pins the timestamp handling, including
// the UTC round trip through SQLite's TEXT storage.
func TestStoreTimestampsUseInjectedClock(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	tokyo, err := time.LoadLocation("Asia/Tokyo")
	if err != nil {
		t.Skipf("timezone database unavailable: %v", err)
	}
	fixed := time.Date(2024, 3, 1, 12, 0, 0, 0, tokyo)
	store.now = func() time.Time { return fixed }

	created, err := store.Create(ctx, BookInput{Title: "T", Author: "A"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if !created.CreatedAt.Equal(fixed) {
		t.Errorf("CreatedAt = %v, want %v", created.CreatedAt, fixed)
	}
	if got, want := created.CreatedAt.Location(), time.UTC; got != want {
		t.Errorf("CreatedAt location = %v, want %v", got, want)
	}

	later := fixed.Add(48 * time.Hour)
	store.now = func() time.Time { return later }
	updated, err := store.Update(ctx, created.ID, BookInput{Title: "T2", Author: "A"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if !updated.UpdatedAt.Equal(later) || !updated.CreatedAt.Equal(fixed) {
		t.Errorf("timestamps = (%v, %v), want (%v, %v)",
			updated.CreatedAt, updated.UpdatedAt, fixed, later)
	}
}

func TestEscapeLike(t *testing.T) {
	tests := []struct{ in, want string }{
		{"Gibson", "Gibson"},
		{"100%", `100\%`},
		{"a_b", `a\_b`},
		{`back\slash`, `back\\slash`},
	}
	for _, tc := range tests {
		if got := escapeLike(tc.in); got != tc.want {
			t.Errorf("escapeLike(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}
