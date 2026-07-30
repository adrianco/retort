package books

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

// newStore opens an empty store backed by a throwaway file. A file rather than
// an in-memory database keeps each test isolated, since SQLite's shared-cache
// in-memory database is process-wide.
func newStore(t *testing.T) *Store {
	t.Helper()

	store, err := Open(t.Context(), filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("Close: %v", err)
		}
	})
	return store
}

func mustCreate(t *testing.T, store *Store, in Input) Book {
	t.Helper()

	book, err := store.Create(t.Context(), in)
	if err != nil {
		t.Fatalf("Create(%+v): %v", in, err)
	}
	return book
}

func TestStoreCreateAndGet(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	before := time.Now().UTC().Add(-time.Second)
	input := Input{Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015, ISBN: "9780134190440"}
	created := mustCreate(t, store, input)

	if created.ID < 1 {
		t.Errorf("Create assigned ID %d, want a positive integer", created.ID)
	}
	if created.Title != input.Title || created.Author != input.Author ||
		created.Year != input.Year || created.ISBN != input.ISBN {
		t.Errorf("Create returned %+v, want the fields of %+v", created, input)
	}
	if created.CreatedAt.Before(before) || created.CreatedAt.After(time.Now().UTC().Add(time.Second)) {
		t.Errorf("CreatedAt = %v, want roughly now", created.CreatedAt)
	}
	if !created.CreatedAt.Equal(created.UpdatedAt) {
		t.Errorf("CreatedAt = %v and UpdatedAt = %v differ on a fresh book", created.CreatedAt, created.UpdatedAt)
	}

	got, err := store.Get(t.Context(), created.ID)
	if err != nil {
		t.Fatalf("Get(%d): %v", created.ID, err)
	}
	assertSameBook(t, got, created)
}

func TestStoreCreateAssignsDistinctIDs(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	seen := make(map[int64]bool)
	for i := range 5 {
		book := mustCreate(t, store, Input{Title: "Book", Author: "Author"})
		if seen[book.ID] {
			t.Fatalf("book %d reused ID %d", i, book.ID)
		}
		seen[book.ID] = true
	}
}

func TestStoreUpdateReplacesEveryField(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	created := mustCreate(t, store, Input{Title: "First Edition", Author: "A. Author", Year: 1999, ISBN: "0306406152"})

	// PUT semantics: the omitted year and ISBN are cleared, not preserved.
	updated, err := store.Update(t.Context(), created.ID, Input{Title: "Second Edition", Author: "B. Author"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}

	if updated.ID != created.ID {
		t.Errorf("Update changed the ID from %d to %d", created.ID, updated.ID)
	}
	if updated.Title != "Second Edition" || updated.Author != "B. Author" {
		t.Errorf("Update returned title %q author %q, want the new values", updated.Title, updated.Author)
	}
	if updated.Year != 0 || updated.ISBN != "" {
		t.Errorf("Update left year %d and isbn %q behind, want them cleared", updated.Year, updated.ISBN)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("CreatedAt changed from %v to %v", created.CreatedAt, updated.CreatedAt)
	}
	if updated.UpdatedAt.Before(created.UpdatedAt) {
		t.Errorf("UpdatedAt went backwards: %v then %v", created.UpdatedAt, updated.UpdatedAt)
	}

	// The update must be visible to a fresh read, not just in the return value.
	reread, err := store.Get(t.Context(), created.ID)
	if err != nil {
		t.Fatalf("Get after Update: %v", err)
	}
	assertSameBook(t, reread, updated)
}

func TestStoreDelete(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	created := mustCreate(t, store, Input{Title: "Ephemeral", Author: "A"})
	if err := store.Delete(t.Context(), created.ID); err != nil {
		t.Fatalf("Delete(%d): %v", created.ID, err)
	}

	if _, err := store.Get(t.Context(), created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete = %v, want ErrNotFound", err)
	}
	if err := store.Delete(t.Context(), created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("second Delete = %v, want ErrNotFound", err)
	}
}

func TestStoreMissingBook(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	const missing = 4242

	if _, err := store.Get(t.Context(), missing); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get(%d) = %v, want ErrNotFound", missing, err)
	}
	if _, err := store.Update(t.Context(), missing, Input{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update(%d) = %v, want ErrNotFound", missing, err)
	}
	if err := store.Delete(t.Context(), missing); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete(%d) = %v, want ErrNotFound", missing, err)
	}
}

func TestStoreRejectsDuplicateISBN(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	first := mustCreate(t, store, Input{Title: "Original", Author: "A", ISBN: "0306406152"})

	if _, err := store.Create(t.Context(), Input{Title: "Copy", Author: "B", ISBN: "0306406152"}); !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("Create with a duplicate ISBN = %v, want ErrDuplicateISBN", err)
	}

	other := mustCreate(t, store, Input{Title: "Other", Author: "C", ISBN: "9780306406157"})
	if _, err := store.Update(t.Context(), other.ID, Input{Title: "Other", Author: "C", ISBN: first.ISBN}); !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("Update onto a taken ISBN = %v, want ErrDuplicateISBN", err)
	}

	// A book may keep its own ISBN across an update.
	if _, err := store.Update(t.Context(), first.ID, Input{Title: "Original, revised", Author: "A", ISBN: first.ISBN}); err != nil {
		t.Errorf("Update keeping the same ISBN = %v, want nil", err)
	}
}

// TestStoreAllowsManyBooksWithoutISBN pins the reason the uniqueness index is
// partial: the ISBN is optional, so "no ISBN" must not collide with itself.
func TestStoreAllowsManyBooksWithoutISBN(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	for i := range 3 {
		if _, err := store.Create(t.Context(), Input{Title: "Untitled", Author: "Anon"}); err != nil {
			t.Fatalf("Create %d without an ISBN: %v", i, err)
		}
	}

	list, err := store.List(t.Context(), "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(list) != 3 {
		t.Errorf("stored %d books, want 3", len(list))
	}
}

func TestStoreList(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	if list, err := store.List(t.Context(), ""); err != nil {
		t.Fatalf("List on an empty store: %v", err)
	} else if list == nil || len(list) != 0 {
		t.Fatalf("List on an empty store = %v, want an empty non-nil slice", list)
	}

	donovan := mustCreate(t, store, Input{Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015})
	kernighan := mustCreate(t, store, Input{Title: "The Practice of Programming", Author: "Brian Kernighan", Year: 1999})
	donovan2 := mustCreate(t, store, Input{Title: "Another Go Book", Author: "alan donovan", Year: 2020})

	t.Run("returns every book in id order", func(t *testing.T) {
		list, err := store.List(t.Context(), "")
		if err != nil {
			t.Fatalf("List: %v", err)
		}
		assertIDs(t, list, donovan.ID, kernighan.ID, donovan2.ID)
	})

	t.Run("filters by author", func(t *testing.T) {
		list, err := store.List(t.Context(), "Brian Kernighan")
		if err != nil {
			t.Fatalf("List: %v", err)
		}
		assertIDs(t, list, kernighan.ID)
	})

	t.Run("author match ignores case and surrounding space", func(t *testing.T) {
		for _, query := range []string{"Alan Donovan", "alan donovan", "ALAN DONOVAN", "  Alan Donovan  "} {
			list, err := store.List(t.Context(), query)
			if err != nil {
				t.Fatalf("List(%q): %v", query, err)
			}
			assertIDs(t, list, donovan.ID, donovan2.ID)
		}
	})

	t.Run("unknown author yields an empty list", func(t *testing.T) {
		list, err := store.List(t.Context(), "Nobody At All")
		if err != nil {
			t.Fatalf("List: %v", err)
		}
		if len(list) != 0 {
			t.Errorf("List for an unknown author returned %d books, want 0", len(list))
		}
	})

	t.Run("partial author names do not match", func(t *testing.T) {
		list, err := store.List(t.Context(), "Donovan")
		if err != nil {
			t.Fatalf("List: %v", err)
		}
		if len(list) != 0 {
			t.Errorf("List(%q) returned %d books, want 0: the filter is an exact match", "Donovan", len(list))
		}
	})
}

// TestStorePersistsAcrossRestart is what distinguishes the SQLite store from a
// map: reopening the same file must show the same books.
func TestStorePersistsAcrossRestart(t *testing.T) {
	t.Parallel()

	path := filepath.Join(t.TempDir(), "books.db")

	first, err := Open(t.Context(), path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	created := mustCreate(t, first, Input{Title: "Durable", Author: "A. Author", Year: 2001, ISBN: "0306406152"})
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	second, err := Open(t.Context(), path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer second.Close()

	got, err := second.Get(t.Context(), created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	assertSameBook(t, got, created)
}

func TestStoreOpenInMemory(t *testing.T) {
	t.Parallel()

	store, err := Open(t.Context(), InMemoryPath)
	if err != nil {
		t.Fatalf("Open(InMemoryPath): %v", err)
	}
	defer store.Close()

	if _, err := store.Create(t.Context(), Input{Title: "Transient", Author: "A"}); err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Ping(t.Context()); err != nil {
		t.Errorf("Ping: %v", err)
	}
}

func TestStorePingFailsAfterClose(t *testing.T) {
	t.Parallel()

	store, err := Open(t.Context(), filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	if err := store.Ping(t.Context()); err != nil {
		t.Fatalf("Ping on an open store: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	if err := store.Ping(context.Background()); err == nil {
		t.Error("Ping on a closed store = nil, want an error so /health can report it")
	}
}

// TestStoreConcurrentWrites exercises the pool settings: parallel writers must
// not trip over SQLITE_BUSY or hand out duplicate IDs.
func TestStoreConcurrentWrites(t *testing.T) {
	t.Parallel()
	store := newStore(t)

	const writers = 24

	var (
		wg   sync.WaitGroup
		mu   sync.Mutex
		ids  = make(map[int64]bool, writers)
		errs []error
	)
	for range writers {
		wg.Add(1)
		go func() {
			defer wg.Done()

			book, err := store.Create(context.Background(), Input{Title: "Concurrent", Author: "A"})
			mu.Lock()
			defer mu.Unlock()
			if err != nil {
				errs = append(errs, err)
				return
			}
			if ids[book.ID] {
				errs = append(errs, errors.New("duplicate id assigned"))
			}
			ids[book.ID] = true
		}()
	}
	wg.Wait()

	for _, err := range errs {
		t.Errorf("concurrent Create: %v", err)
	}
	if len(ids) != writers {
		t.Errorf("stored %d distinct books, want %d", len(ids), writers)
	}
}

func assertSameBook(t *testing.T, got, want Book) {
	t.Helper()

	if got.ID != want.ID || got.Title != want.Title || got.Author != want.Author ||
		got.Year != want.Year || got.ISBN != want.ISBN {
		t.Errorf("book = %+v, want %+v", got, want)
	}
	// Timestamps travel through SQLite as RFC 3339 text, so compare instants
	// rather than struct fields.
	if !got.CreatedAt.Equal(want.CreatedAt) {
		t.Errorf("CreatedAt = %v, want %v", got.CreatedAt, want.CreatedAt)
	}
	if !got.UpdatedAt.Equal(want.UpdatedAt) {
		t.Errorf("UpdatedAt = %v, want %v", got.UpdatedAt, want.UpdatedAt)
	}
}

func assertIDs(t *testing.T, list []Book, want ...int64) {
	t.Helper()

	got := make([]int64, len(list))
	for i, book := range list {
		got[i] = book.ID
	}
	if len(got) != len(want) {
		t.Fatalf("got book ids %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got book ids %v, want %v", got, want)
		}
	}
}
