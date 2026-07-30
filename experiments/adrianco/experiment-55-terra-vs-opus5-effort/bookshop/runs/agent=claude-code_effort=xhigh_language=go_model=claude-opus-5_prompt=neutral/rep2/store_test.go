package main

import (
	"context"
	"errors"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

// newTestStore returns a Store backed by a fresh database file in the test's
// temporary directory. A file (rather than ":memory:") is used so the store
// runs with the same multi-connection pool as production.
func newTestStore(t *testing.T) *Store {
	t.Helper()

	store, err := OpenStore(context.Background(), filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("Store.Close: %v", err)
		}
	})
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

func TestStoreCreateAndGet(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created := mustCreate(t, store, Book{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
		Year:   intPtr(2015),
		ISBN:   "9780134190440",
	})

	if created.ID == 0 {
		t.Error("Create() did not assign an ID")
	}
	if created.CreatedAt.IsZero() || created.UpdatedAt.IsZero() {
		t.Errorf("Create() left timestamps zero: %+v", created)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get(%d): %v", created.ID, err)
	}
	// A round trip through SQLite must not lose or alter a single field.
	if got.Title != created.Title || got.Author != created.Author || got.ISBN != created.ISBN {
		t.Errorf("Get() = %+v, want %+v", got, created)
	}
	if got.Year == nil || *got.Year != 2015 {
		t.Errorf("Get().Year = %v, want 2015", got.Year)
	}
	if !got.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("Get().CreatedAt = %v, want %v", got.CreatedAt, created.CreatedAt)
	}
	if !got.UpdatedAt.Equal(created.UpdatedAt) {
		t.Errorf("Get().UpdatedAt = %v, want %v", got.UpdatedAt, created.UpdatedAt)
	}
}

func TestStoreGetMissing(t *testing.T) {
	store := newTestStore(t)

	if _, err := store.Get(context.Background(), 404); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get(404) error = %v, want ErrNotFound", err)
	}
}

// A book with no year or ISBN stores NULL rather than 0 or "", so the values
// come back as "absent" and not as data the client never supplied.
func TestStoreOptionalFieldsRoundTripAsAbsent(t *testing.T) {
	store := newTestStore(t)

	created := mustCreate(t, store, Book{Title: "Beowulf", Author: "Unknown"})

	got, err := store.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Year != nil {
		t.Errorf("Year = %d, want nil", *got.Year)
	}
	if got.ISBN != "" {
		t.Errorf("ISBN = %q, want empty", got.ISBN)
	}
}

func TestStoreListOrdersByID(t *testing.T) {
	store := newTestStore(t)

	first := mustCreate(t, store, Book{Title: "A", Author: "Author One"})
	second := mustCreate(t, store, Book{Title: "B", Author: "Author Two"})
	third := mustCreate(t, store, Book{Title: "C", Author: "Author One"})

	books, err := store.List(context.Background(), ListFilter{})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != 3 {
		t.Fatalf("List() returned %d books, want 3", len(books))
	}
	for i, want := range []int64{first.ID, second.ID, third.ID} {
		if books[i].ID != want {
			t.Errorf("List()[%d].ID = %d, want %d", i, books[i].ID, want)
		}
	}
}

func TestStoreListEmptyIsNotNil(t *testing.T) {
	store := newTestStore(t)

	books, err := store.List(context.Background(), ListFilter{})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if books == nil {
		t.Fatal("List() returned nil; want an empty non-nil slice so it encodes as []")
	}
	if len(books) != 0 {
		t.Fatalf("List() returned %d books, want 0", len(books))
	}
}

func TestStoreListFilterByAuthor(t *testing.T) {
	store := newTestStore(t)

	mustCreate(t, store, Book{Title: "Dune", Author: "Frank Herbert"})
	mustCreate(t, store, Book{Title: "Dune Messiah", Author: "Frank Herbert"})
	mustCreate(t, store, Book{Title: "Neuromancer", Author: "William Gibson"})

	tests := []struct {
		filter string
		want   int
	}{
		{"Frank Herbert", 2},
		{"frank herbert", 2}, // the filter is case-insensitive
		{"FRANK HERBERT", 2},
		{"William Gibson", 1},
		{"Ursula K. Le Guin", 0},
		{"Frank", 0}, // and matches the whole field, not a prefix
	}

	for _, tt := range tests {
		books, err := store.List(context.Background(), ListFilter{Author: tt.filter})
		if err != nil {
			t.Fatalf("List(author=%q): %v", tt.filter, err)
		}
		if len(books) != tt.want {
			t.Errorf("List(author=%q) returned %d books, want %d", tt.filter, len(books), tt.want)
		}
		for _, b := range books {
			if !strings.EqualFold(b.Author, tt.filter) {
				t.Errorf("List(author=%q) returned a book by %q", tt.filter, b.Author)
			}
		}
	}
}

func TestStoreUpdateReplacesFieldsAndPreservesCreatedAt(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created := mustCreate(t, store, Book{
		Title:  "The Go Programming Langauge", // typo to be fixed
		Author: "Alan Donovan",
		Year:   intPtr(2015),
		ISBN:   "9780134190440",
	})

	// Pin the clock forward so the updated_at change is unambiguous.
	later := created.CreatedAt.Add(time.Hour)
	store.now = func() time.Time { return later }

	// A full replacement: the omitted year and ISBN must be cleared.
	updated, err := store.Update(ctx, created.ID, Book{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
	})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.ID != created.ID {
		t.Errorf("Update().ID = %d, want %d", updated.ID, created.ID)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("Update().CreatedAt = %v, want it preserved as %v", updated.CreatedAt, created.CreatedAt)
	}
	if !updated.UpdatedAt.Equal(later) {
		t.Errorf("Update().UpdatedAt = %v, want %v", updated.UpdatedAt, later)
	}

	got, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after Update: %v", err)
	}
	if got.Title != "The Go Programming Language" || got.Author != "Alan A. A. Donovan" {
		t.Errorf("Get after Update = %+v, want the replaced title and author", got)
	}
	if got.Year != nil {
		t.Errorf("Get after Update .Year = %d, want nil (cleared)", *got.Year)
	}
	if got.ISBN != "" {
		t.Errorf("Get after Update .ISBN = %q, want empty (cleared)", got.ISBN)
	}
	if !got.UpdatedAt.Equal(later) {
		t.Errorf("persisted UpdatedAt = %v, want %v", got.UpdatedAt, later)
	}
}

func TestStoreUpdateMissing(t *testing.T) {
	store := newTestStore(t)

	_, err := store.Update(context.Background(), 404, Book{Title: "Ghost", Author: "Nobody"})
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("Update(404) error = %v, want ErrNotFound", err)
	}
}

func TestStoreDelete(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	created := mustCreate(t, store, Book{Title: "Ephemeral", Author: "Someone"})

	if err := store.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete error = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("second Delete error = %v, want ErrNotFound", err)
	}
}

// TestStoreDuplicateISBN pins the driver error mapping that isUniqueViolation
// depends on: a UNIQUE violation must surface as ErrISBNTaken and nothing else.
func TestStoreDuplicateISBN(t *testing.T) {
	ctx := context.Background()
	store := newTestStore(t)

	first := mustCreate(t, store, Book{Title: "Dune", Author: "Frank Herbert", ISBN: "9780441013593"})
	second := mustCreate(t, store, Book{Title: "Dune Messiah", Author: "Frank Herbert", ISBN: "9780593098233"})

	_, err := store.Create(ctx, Book{Title: "Dune (reprint)", Author: "Frank Herbert", ISBN: first.ISBN})
	if !errors.Is(err, ErrISBNTaken) {
		t.Fatalf("Create with duplicate ISBN error = %v, want ErrISBNTaken", err)
	}

	// The same guard applies to updates.
	_, err = store.Update(ctx, second.ID, Book{Title: "Dune Messiah", Author: "Frank Herbert", ISBN: first.ISBN})
	if !errors.Is(err, ErrISBNTaken) {
		t.Fatalf("Update to a duplicate ISBN error = %v, want ErrISBNTaken", err)
	}

	// Re-writing a book's own ISBN is not a conflict.
	if _, err := store.Update(ctx, first.ID, Book{Title: "Dune", Author: "Frank Herbert", ISBN: first.ISBN}); err != nil {
		t.Fatalf("Update keeping its own ISBN: %v", err)
	}
}

// The ISBN column is UNIQUE but nullable, so any number of books may have no
// ISBN at all.
func TestStoreManyBooksWithoutISBN(t *testing.T) {
	store := newTestStore(t)

	for i := 0; i < 3; i++ {
		mustCreate(t, store, Book{Title: "Untitled", Author: "Anonymous"})
	}

	books, err := store.List(context.Background(), ListFilter{})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != 3 {
		t.Fatalf("List() returned %d books, want 3", len(books))
	}
}

// Concurrent writers must not fail with SQLITE_BUSY: the pool relies on WAL
// plus a busy timeout to serialise them.
func TestStoreConcurrentCreates(t *testing.T) {
	store := newTestStore(t)

	const writers = 16
	var (
		wg   sync.WaitGroup
		mu   sync.Mutex
		errs []error
	)
	for i := 0; i < writers; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			_, err := store.Create(context.Background(), Book{
				Title:  "Concurrent",
				Author: "Writer",
				Year:   intPtr(2000 + i),
			})
			if err != nil {
				mu.Lock()
				errs = append(errs, err)
				mu.Unlock()
			}
		}(i)
	}
	wg.Wait()

	if len(errs) > 0 {
		t.Fatalf("%d of %d concurrent Create calls failed; first error: %v", len(errs), writers, errs[0])
	}

	books, err := store.List(context.Background(), ListFilter{})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != writers {
		t.Errorf("List() returned %d books, want %d", len(books), writers)
	}
}

// An in-memory database is the documented option for ephemeral runs, so it
// has to work end to end despite needing a single connection.
func TestStoreInMemory(t *testing.T) {
	ctx := context.Background()

	store, err := OpenStore(ctx, ":memory:")
	if err != nil {
		t.Fatalf("OpenStore(:memory:): %v", err)
	}
	defer store.Close()

	created := mustCreate(t, store, Book{Title: "Transient", Author: "Someone"})
	if _, err := store.Get(ctx, created.ID); err != nil {
		t.Fatalf("Get from in-memory store: %v", err)
	}
}

func TestBuildDSN(t *testing.T) {
	tests := []struct {
		path       string
		inMemory   bool
		wantSubstr []string
		wantAbsent []string
	}{
		{
			path:       "books.db",
			wantSubstr: []string{"books.db?", "busy_timeout%285000%29", "journal_mode%28WAL%29"},
		},
		{
			// journal_mode is meaningless without a file to persist it in.
			path:       ":memory:",
			inMemory:   true,
			wantSubstr: []string{":memory:?", "busy_timeout%285000%29"},
			wantAbsent: []string{"journal_mode"},
		},
		{
			// A path that already carries driver options keeps them.
			path:       "file:books.db?_txlock=immediate",
			wantSubstr: []string{"file:books.db?_txlock=immediate&", "journal_mode%28WAL%29"},
		},
	}

	for _, tt := range tests {
		got := buildDSN(tt.path, tt.inMemory)
		for _, want := range tt.wantSubstr {
			if !strings.Contains(got, want) {
				t.Errorf("buildDSN(%q, %v) = %q, want it to contain %q", tt.path, tt.inMemory, got, want)
			}
		}
		for _, unwanted := range tt.wantAbsent {
			if strings.Contains(got, unwanted) {
				t.Errorf("buildDSN(%q, %v) = %q, want it to omit %q", tt.path, tt.inMemory, got, unwanted)
			}
		}
	}
}

func TestIsMemoryPath(t *testing.T) {
	for path, want := range map[string]bool{
		":memory:":                        true,
		"file:test.db?mode=memory":        true,
		"file::memory:?cache=shared":      true,
		"books.db":                        false,
		"/var/lib/bookapi/books.db":       false,
		"file:books.db?_txlock=immediate": false,
	} {
		if got := isMemoryPath(path); got != want {
			t.Errorf("isMemoryPath(%q) = %v, want %v", path, got, want)
		}
	}
}

func TestOpenStoreRejectsUnwritablePath(t *testing.T) {
	_, err := OpenStore(context.Background(), filepath.Join(t.TempDir(), "no-such-dir", "books.db"))
	if err == nil {
		t.Fatal("OpenStore() succeeded for a path in a nonexistent directory, want an error")
	}
}
