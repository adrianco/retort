package main

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

// fakeClock hands out a deterministic, strictly increasing sequence of times so
// tests can assert on created_at/updated_at without racing the wall clock.
type fakeClock struct {
	mu   sync.Mutex
	now  time.Time
	step time.Duration
}

func newFakeClock() *fakeClock {
	return &fakeClock{
		now:  time.Date(2024, time.March, 14, 15, 9, 26, 535897000, time.UTC),
		step: time.Second,
	}
}

func (c *fakeClock) Now() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	t := c.now
	c.now = c.now.Add(c.step)
	return t
}

// newTestStore opens a throwaway SQLite database backed by a real file, so the
// tests exercise the same code path as production (WAL, file locking and all).
func newTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("closing store: %v", err)
		}
	})
	store.now = newFakeClock().Now
	return store
}

func mustCreate(t *testing.T, s *Store, in BookInput) *Book {
	t.Helper()
	in.Clean()
	if err := in.Validate(referenceNow); err != nil {
		t.Fatalf("fixture %q is itself invalid: %v", in.Title, err)
	}
	book, err := s.Create(context.Background(), in)
	if err != nil {
		t.Fatalf("Create(%q): %v", in.Title, err)
	}
	return book
}

func TestStoreCreateAndGetRoundTrip(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, store, BookInput{
		Title:  "The Hitchhiker's Guide to the Galaxy",
		Author: "Douglas Adams",
		Year:   ptr(1979),
		ISBN:   ptr("0345391802"),
	})

	if created.ID <= 0 {
		t.Fatalf("Create returned id %d, want a positive id", created.ID)
	}
	if created.CreatedAt.IsZero() || !created.CreatedAt.Equal(created.UpdatedAt) {
		t.Errorf("new book should have equal non-zero timestamps, got created=%v updated=%v",
			created.CreatedAt, created.UpdatedAt)
	}

	fetched, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get(%d): %v", created.ID, err)
	}
	assertBookEqual(t, fetched, created)
}

func TestStoreCreateWithoutOptionalFields(t *testing.T) {
	store := newTestStore(t)

	created := mustCreate(t, store, BookInput{Title: "Untitled Draft", Author: "Anon"})

	fetched, err := store.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if fetched.Year != nil {
		t.Errorf("Year = %d, want nil", *fetched.Year)
	}
	if fetched.ISBN != nil {
		t.Errorf("ISBN = %q, want nil", *fetched.ISBN)
	}
}

func TestStoreGetMissingReturnsErrNotFound(t *testing.T) {
	store := newTestStore(t)

	if _, err := store.Get(context.Background(), 4242); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get(4242) error = %v, want ErrNotFound", err)
	}
}

func TestStoreListFiltersByAuthorCaseInsensitively(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	mustCreate(t, store, BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965)})
	mustCreate(t, store, BookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: ptr(1969)})
	mustCreate(t, store, BookInput{Title: "Neuromancer", Author: "William Gibson", Year: ptr(1984)})

	all, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List(all): %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("List(all) returned %d books, want 3", len(all))
	}
	// Results are ordered by id, i.e. insertion order.
	if all[0].Title != "Dune" || all[2].Title != "Neuromancer" {
		t.Errorf("List(all) out of order: %q ... %q", all[0].Title, all[2].Title)
	}

	for _, query := range []string{"Frank Herbert", "frank herbert", "FRANK HERBERT"} {
		filtered, err := store.List(ctx, query)
		if err != nil {
			t.Fatalf("List(%q): %v", query, err)
		}
		if len(filtered) != 2 {
			t.Errorf("List(%q) returned %d books, want 2", query, len(filtered))
			continue
		}
		for _, b := range filtered {
			if b.Author != "Frank Herbert" {
				t.Errorf("List(%q) returned a book by %q", query, b.Author)
			}
		}
	}

	none, err := store.List(ctx, "Nobody At All")
	if err != nil {
		t.Fatalf("List(unknown author): %v", err)
	}
	if none == nil {
		t.Error("List returned a nil slice; it must be empty-but-not-nil so it marshals to []")
	}
	if len(none) != 0 {
		t.Errorf("List(unknown author) returned %d books, want 0", len(none))
	}
}

func TestStoreUpdateReplacesEveryClientField(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, store, BookInput{
		Title:  "Neuromancer",
		Author: "Wiliam Gibsn", // to be corrected below
		Year:   ptr(1984),
		ISBN:   ptr("0441569560"),
	})

	// Omitting year and isbn must clear them: PUT replaces the whole record.
	updated, err := store.Update(ctx, created.ID, BookInput{Title: "Neuromancer", Author: "William Gibson"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}

	if updated.Author != "William Gibson" {
		t.Errorf("Author = %q, want %q", updated.Author, "William Gibson")
	}
	if updated.Year != nil {
		t.Errorf("Year = %d, want nil after an update that omitted it", *updated.Year)
	}
	if updated.ISBN != nil {
		t.Errorf("ISBN = %q, want nil after an update that omitted it", *updated.ISBN)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("CreatedAt changed: %v -> %v", created.CreatedAt, updated.CreatedAt)
	}
	if !updated.UpdatedAt.After(created.UpdatedAt) {
		t.Errorf("UpdatedAt = %v, want later than %v", updated.UpdatedAt, created.UpdatedAt)
	}

	// The response must match what was actually committed.
	fetched, err := store.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after update: %v", err)
	}
	assertBookEqual(t, fetched, updated)
}

func TestStoreUpdateMissingReturnsErrNotFound(t *testing.T) {
	store := newTestStore(t)

	_, err := store.Update(context.Background(), 999, BookInput{Title: "Ghost", Author: "Nobody"})
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("Update(999) error = %v, want ErrNotFound", err)
	}
}

func TestStoreDelete(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	created := mustCreate(t, store, BookInput{Title: "Ephemeral", Author: "Someone"})

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

func TestStoreISBNUniqueness(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	mustCreate(t, store, BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("9780441013593")})

	t.Run("create with a taken isbn", func(t *testing.T) {
		_, err := store.Create(ctx, BookInput{Title: "Dune (reprint)", Author: "Frank Herbert", ISBN: ptr("9780441013593")})
		if !errors.Is(err, ErrDuplicateISBN) {
			t.Fatalf("Create error = %v, want ErrDuplicateISBN", err)
		}
	})

	t.Run("update onto a taken isbn", func(t *testing.T) {
		other := mustCreate(t, store, BookInput{Title: "Neuromancer", Author: "William Gibson", ISBN: ptr("0441569560")})
		_, err := store.Update(ctx, other.ID, BookInput{Title: "Neuromancer", Author: "William Gibson", ISBN: ptr("9780441013593")})
		if !errors.Is(err, ErrDuplicateISBN) {
			t.Fatalf("Update error = %v, want ErrDuplicateISBN", err)
		}
	})

	t.Run("any number of books may have no isbn", func(t *testing.T) {
		mustCreate(t, store, BookInput{Title: "Draft One", Author: "Anon"})
		mustCreate(t, store, BookInput{Title: "Draft Two", Author: "Anon"})
	})
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created := mustCreate(t, store, BookInput{Title: "Persistent", Author: "Author", Year: ptr(2001)})
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	t.Cleanup(func() { reopened.Close() })

	fetched, err := reopened.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	assertBookEqual(t, fetched, created)
}

func TestStoreConcurrentCreates(t *testing.T) {
	store := newTestStore(t)
	ctx := context.Background()

	const writers = 24
	var wg sync.WaitGroup
	errs := make(chan error, writers)
	ids := make(chan int64, writers)

	for i := range writers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			book, err := store.Create(ctx, BookInput{
				Title:  "Concurrent",
				Author: "Racer",
				Year:   ptr(2000 + i%20),
			})
			if err != nil {
				errs <- err
				return
			}
			ids <- book.ID
		}()
	}
	wg.Wait()
	close(errs)
	close(ids)

	for err := range errs {
		t.Errorf("concurrent Create failed: %v", err)
	}

	seen := make(map[int64]bool, writers)
	for id := range ids {
		if seen[id] {
			t.Errorf("id %d was handed out twice", id)
		}
		seen[id] = true
	}
	if len(seen) != writers {
		t.Fatalf("got %d successful writes, want %d", len(seen), writers)
	}

	all, err := store.List(ctx, "Racer")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != writers {
		t.Errorf("List returned %d books, want %d", len(all), writers)
	}
}

func TestOpenStoreInMemory(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore(:memory:): %v", err)
	}
	defer store.Close()

	created := mustCreate(t, store, BookInput{Title: "Transient", Author: "Author"})
	if _, err := store.Get(context.Background(), created.ID); err != nil {
		t.Fatalf("Get from in-memory store: %v", err)
	}
}

// assertBookEqual compares two books field by field, which gives a far more
// useful failure message than reflect.DeepEqual on structs full of pointers.
func assertBookEqual(t *testing.T, got, want *Book) {
	t.Helper()
	if got.ID != want.ID {
		t.Errorf("ID = %d, want %d", got.ID, want.ID)
	}
	if got.Title != want.Title {
		t.Errorf("Title = %q, want %q", got.Title, want.Title)
	}
	if got.Author != want.Author {
		t.Errorf("Author = %q, want %q", got.Author, want.Author)
	}
	if !equalPtr(got.Year, want.Year) {
		t.Errorf("Year = %s, want %s", showPtr(got.Year), showPtr(want.Year))
	}
	if !equalPtr(got.ISBN, want.ISBN) {
		t.Errorf("ISBN = %s, want %s", showPtr(got.ISBN), showPtr(want.ISBN))
	}
	if !got.CreatedAt.Equal(want.CreatedAt) {
		t.Errorf("CreatedAt = %v, want %v", got.CreatedAt, want.CreatedAt)
	}
	if !got.UpdatedAt.Equal(want.UpdatedAt) {
		t.Errorf("UpdatedAt = %v, want %v", got.UpdatedAt, want.UpdatedAt)
	}
}

func equalPtr[T comparable](a, b *T) bool {
	if a == nil || b == nil {
		return a == b
	}
	return *a == *b
}

func showPtr[T any](p *T) string {
	if p == nil {
		return "<nil>"
	}
	return fmt.Sprintf("%v", *p)
}
