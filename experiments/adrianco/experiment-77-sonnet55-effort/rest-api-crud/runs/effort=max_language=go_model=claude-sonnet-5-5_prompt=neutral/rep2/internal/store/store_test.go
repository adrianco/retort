package store_test

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"

	"bookapi/internal/book"
	"bookapi/internal/store"
)

var ctx = context.Background()

func newStore(t *testing.T) *store.Store {
	t.Helper()
	s, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() {
		if err := s.Close(); err != nil {
			t.Errorf("Close: %v", err)
		}
	})
	return s
}

func create(t *testing.T, s *store.Store, title, author string) book.Book {
	t.Helper()
	b, err := s.Create(ctx, book.Input{Title: title, Author: author})
	if err != nil {
		t.Fatalf("Create(%q, %q): %v", title, author, err)
	}
	return b
}

func titles(books []book.Book) []string {
	out := make([]string, len(books))
	for i, b := range books {
		out[i] = b.Title
	}
	return out
}

func equalStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func TestCreateAndGet(t *testing.T) {
	s := newStore(t)

	in := book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441013593"}
	created, err := s.Create(ctx, in)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	want := book.Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441013593"}
	if created.ID <= 0 {
		t.Errorf("Create returned ID %d, want a positive ID", created.ID)
	}
	if created != want {
		t.Errorf("Create = %+v, want %+v", created, want)
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != want {
		t.Errorf("Get = %+v, want %+v", got, want)
	}
}

func TestOptionalFieldsDefault(t *testing.T) {
	s := newStore(t)

	b := create(t, s, "Untitled Notes", "Anonymous")
	if b.Year != 0 || b.ISBN != "" {
		t.Errorf("optional fields = year %d, isbn %q; want 0 and empty", b.Year, b.ISBN)
	}
}

func TestGetMissing(t *testing.T) {
	s := newStore(t)

	for _, id := range []int64{1, 0, -1, 1 << 40} {
		if _, err := s.Get(ctx, id); !errors.Is(err, book.ErrNotFound) {
			t.Errorf("Get(%d) error = %v, want book.ErrNotFound", id, err)
		}
	}
}

func TestListOrdersByIDAndNeverReturnsNil(t *testing.T) {
	s := newStore(t)

	empty, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List on empty store: %v", err)
	}
	if empty == nil || len(empty) != 0 {
		t.Errorf("List on empty store = %#v, want a non-nil empty slice", empty)
	}

	create(t, s, "B", "x")
	create(t, s, "A", "y")
	create(t, s, "C", "z")

	got, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if want := []string{"B", "A", "C"}; !equalStrings(titles(got), want) {
		t.Errorf("List titles = %v, want %v (insertion order)", titles(got), want)
	}
}

func TestListFiltersByAuthor(t *testing.T) {
	s := newStore(t)
	create(t, s, "1984", "George Orwell")
	create(t, s, "Emma", "Jane Austen")
	create(t, s, "Animal Farm", "George Orwell")
	create(t, s, "Homage to Catalonia", "George Orwell Jr.")

	tests := []struct {
		name   string
		author string
		want   []string
	}{
		{"exact match", "George Orwell", []string{"1984", "Animal Farm"}},
		{"case-insensitive", "gEoRgE oRWELL", []string{"1984", "Animal Farm"}},
		{"not a substring match", "Orwell", nil},
		{"unknown author", "Nobody", nil},
		{"LIKE wildcards are literal", "%", nil},
		{"underscore is literal", "Jane_Austen", nil},
		{"empty means no filter", "", []string{"1984", "Emma", "Animal Farm", "Homage to Catalonia"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := s.List(ctx, tt.author)
			if err != nil {
				t.Fatalf("List(%q): %v", tt.author, err)
			}
			if !equalStrings(titles(got), tt.want) {
				t.Errorf("List(%q) titles = %v, want %v", tt.author, titles(got), tt.want)
			}
		})
	}
}

func TestUpdate(t *testing.T) {
	s := newStore(t)
	target := create(t, s, "Old Title", "Old Author")
	other := create(t, s, "Untouched", "Someone")

	updated, err := s.Update(ctx, target.ID, book.Input{Title: "New Title", Author: "New Author", Year: 2001, ISBN: "123"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	want := book.Book{ID: target.ID, Title: "New Title", Author: "New Author", Year: 2001, ISBN: "123"}
	if updated != want {
		t.Errorf("Update = %+v, want %+v", updated, want)
	}

	if got, _ := s.Get(ctx, target.ID); got != want {
		t.Errorf("Get after Update = %+v, want %+v", got, want)
	}
	if got, _ := s.Get(ctx, other.ID); got != other {
		t.Errorf("unrelated book changed: got %+v, want %+v", got, other)
	}

	// Update is a full replacement: omitted optional fields are cleared.
	cleared, err := s.Update(ctx, target.ID, book.Input{Title: "T", Author: "A"})
	if err != nil {
		t.Fatalf("Update (clear optional fields): %v", err)
	}
	if cleared.Year != 0 || cleared.ISBN != "" {
		t.Errorf("optional fields after Update = year %d, isbn %q; want 0 and empty", cleared.Year, cleared.ISBN)
	}
}

func TestUpdateMissing(t *testing.T) {
	s := newStore(t)

	_, err := s.Update(ctx, 42, book.Input{Title: "T", Author: "A"})
	if !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Update error = %v, want book.ErrNotFound", err)
	}
	if books, _ := s.List(ctx, ""); len(books) != 0 {
		t.Errorf("Update of a missing book created rows: %+v", books)
	}
}

func TestDelete(t *testing.T) {
	s := newStore(t)
	keep := create(t, s, "Keep", "A")
	drop := create(t, s, "Drop", "B")

	if err := s.Delete(ctx, drop.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, drop.ID); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Get after Delete error = %v, want book.ErrNotFound", err)
	}
	if err := s.Delete(ctx, drop.ID); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("second Delete error = %v, want book.ErrNotFound", err)
	}
	if got, err := s.Get(ctx, keep.ID); err != nil || got != keep {
		t.Errorf("Get(keep) = %+v, %v; want %+v, nil", got, err, keep)
	}
}

func TestIDsAreNotReused(t *testing.T) {
	s := newStore(t)
	last := create(t, s, "First", "A")
	if err := s.Delete(ctx, last.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}

	next := create(t, s, "Second", "A")
	if next.ID <= last.ID {
		t.Errorf("new book got ID %d after ID %d was deleted; IDs must never be reused", next.ID, last.ID)
	}
}

func TestSpecialCharactersAreStoredVerbatim(t *testing.T) {
	s := newStore(t)

	in := book.Input{
		Title:  `Robert'); DROP TABLE books;--`,
		Author: "Zoë Café — 村上春樹 \U0001F4DA",
		ISBN:   `100%_\"`,
	}
	created, err := s.Create(ctx, in)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != in.Title || got.Author != in.Author || got.ISBN != in.ISBN {
		t.Errorf("Get = %+v, want the input stored verbatim: %+v", got, in)
	}
	if books, err := s.List(ctx, ""); err != nil || len(books) != 1 {
		t.Errorf("List = %+v, %v; the table should be intact with exactly one book", books, err)
	}
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	first, err := store.Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	created, err := first.Create(ctx, book.Input{Title: "Durable", Author: "Disk", Year: 2024})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	// Opening an existing database must keep its data (schema setup is idempotent).
	second, err := store.Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer second.Close()

	got, err := second.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("after reopen got %+v, want %+v", got, created)
	}
}

// TestConcurrentUse hammers the store from many goroutines. Against ":memory:"
// it also proves every goroutine sees the same database: if the pool opened a
// second connection, that connection would get its own empty database.
func TestConcurrentUse(t *testing.T) {
	databases := map[string]string{
		"file":   filepath.Join(t.TempDir(), "books.db"),
		"memory": ":memory:",
	}
	for name, path := range databases {
		t.Run(name, func(t *testing.T) {
			s, err := store.Open(path)
			if err != nil {
				t.Fatalf("Open(%q): %v", path, err)
			}
			defer s.Close()

			const workers, perWorker = 8, 25
			var wg sync.WaitGroup
			errs := make(chan error, 2*workers*perWorker)
			for w := range workers {
				wg.Add(1)
				go func() {
					defer wg.Done()
					for i := range perWorker {
						if _, err := s.Create(ctx, book.Input{Title: "T", Author: "A", Year: w*1000 + i}); err != nil {
							errs <- err
						}
						if _, err := s.List(ctx, "A"); err != nil {
							errs <- err
						}
					}
				}()
			}
			wg.Wait()
			close(errs)
			for err := range errs {
				t.Errorf("concurrent use: %v", err)
			}

			books, err := s.List(ctx, "")
			if err != nil {
				t.Fatalf("List: %v", err)
			}
			if len(books) != workers*perWorker {
				t.Errorf("stored %d books, want %d", len(books), workers*perWorker)
			}
			seen := make(map[int64]bool, len(books))
			for _, b := range books {
				if seen[b.ID] {
					t.Fatalf("duplicate ID %d", b.ID)
				}
				seen[b.ID] = true
			}
		})
	}
}

// A broken database must surface as an error, never be mistaken for a missing
// book: the API would otherwise answer 404 instead of 500.
func TestOperationsFailOnClosedStore(t *testing.T) {
	s, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	in := book.Input{Title: "T", Author: "A"}
	_, createErr := s.Create(ctx, in)
	_, getErr := s.Get(ctx, 1)
	_, listErr := s.List(ctx, "")
	_, updateErr := s.Update(ctx, 1, in)
	results := map[string]error{
		"Create": createErr,
		"Get":    getErr,
		"List":   listErr,
		"Update": updateErr,
		"Delete": s.Delete(ctx, 1),
		"Ping":   s.Ping(ctx),
	}
	for op, err := range results {
		if err == nil {
			t.Errorf("%s on a closed store succeeded, want an error", op)
		} else if errors.Is(err, book.ErrNotFound) {
			t.Errorf("%s on a closed store returned ErrNotFound (%v); a database failure is not a missing book", op, err)
		}
	}
}

func TestPing(t *testing.T) {
	s := newStore(t)
	if err := s.Ping(ctx); err != nil {
		t.Errorf("Ping on an open store: %v", err)
	}

	cancelled, cancel := context.WithCancel(ctx)
	cancel()
	if err := s.Ping(cancelled); err == nil {
		t.Error("Ping with a cancelled context succeeded, want an error")
	}
}

func TestOpenRejectsBadPaths(t *testing.T) {
	tests := map[string]string{
		"empty path":            "",
		"contains a query mark": filepath.Join(t.TempDir(), "books.db?mode=ro"),
		"missing directory":     filepath.Join(t.TempDir(), "no-such-dir", "books.db"),
	}
	for name, path := range tests {
		t.Run(name, func(t *testing.T) {
			s, err := store.Open(path)
			if err == nil {
				s.Close()
				t.Fatalf("Open(%q) succeeded, want an error", path)
			}
		})
	}
}
