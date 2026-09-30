package store_test

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"testing"
	"time"

	"bookapi/internal/book"
	"bookapi/internal/store"
)

func openFile(t *testing.T) *store.Store {
	t.Helper()
	return open(t, filepath.Join(t.TempDir(), "books.db"))
}

func open(t *testing.T, path string) *store.Store {
	t.Helper()
	s, err := store.Open(path)
	if err != nil {
		t.Fatalf("Open(%q): %v", path, err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

// eachStore runs fn against a file-backed and an in-memory store, which must
// behave identically.
func eachStore(t *testing.T, fn func(t *testing.T, s *store.Store)) {
	t.Helper()
	t.Run("file", func(t *testing.T) { fn(t, openFile(t)) })
	t.Run("memory", func(t *testing.T) { fn(t, open(t, store.Memory)) })
}

func input(title, author string) book.Input {
	return book.Input{Title: title, Author: author, Year: 2001, ISBN: "isbn-" + title}
}

func mustCreate(t *testing.T, s *store.Store, in book.Input) book.Book {
	t.Helper()
	b, err := s.Create(t.Context(), in)
	if err != nil {
		t.Fatalf("Create(%+v): %v", in, err)
	}
	return b
}

func mustList(t *testing.T, s *store.Store, author string) []book.Book {
	t.Helper()
	books, err := s.List(t.Context(), author)
	if err != nil {
		t.Fatalf("List(%q): %v", author, err)
	}
	return books
}

func titles(books []book.Book) []string {
	out := make([]string, len(books))
	for i, b := range books {
		out[i] = b.Title
	}
	return out
}

func TestCreateAndGet(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		in := book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"}
		created := mustCreate(t, s, in)
		if created.ID <= 0 {
			t.Errorf("Create returned id %d, want a positive id", created.ID)
		}
		if created.Input != in {
			t.Errorf("Create returned %+v, want the input %+v", created.Input, in)
		}

		got, err := s.Get(t.Context(), created.ID)
		if err != nil {
			t.Fatalf("Get: %v", err)
		}
		if got != created {
			t.Errorf("Get = %+v, want %+v", got, created)
		}
	})
}

func TestCreateAssignsIncreasingIDs(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		a := mustCreate(t, s, input("A", "X"))
		b := mustCreate(t, s, input("B", "X"))
		c := mustCreate(t, s, input("C", "X"))
		if !(a.ID < b.ID && b.ID < c.ID) {
			t.Errorf("ids = %d, %d, %d, want strictly increasing", a.ID, b.ID, c.ID)
		}
	})
}

func TestGetMissingBook(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		mustCreate(t, s, input("Only", "One"))
		for _, id := range []int64{0, -1, 999} {
			if _, err := s.Get(t.Context(), id); !errors.Is(err, book.ErrNotFound) {
				t.Errorf("Get(%d) error = %v, want book.ErrNotFound", id, err)
			}
		}
	})
}

func TestListReturnsBooksInIDOrder(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		if got := mustList(t, s, ""); len(got) != 0 {
			t.Fatalf("List on an empty store = %+v, want nothing", got)
		}
		want := []string{"Third", "First", "Second"} // insertion order, not alphabetical
		for _, title := range want {
			mustCreate(t, s, input(title, "Someone"))
		}
		if got := titles(mustList(t, s, "")); !slices.Equal(got, want) {
			t.Errorf("List titles = %v, want %v", got, want)
		}
	})
}

func TestListFiltersByAuthor(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		mustCreate(t, s, input("Nineteen Eighty-Four", "George Orwell"))
		mustCreate(t, s, input("Brave New World", "Aldous Huxley"))
		mustCreate(t, s, input("Animal Farm", "George Orwell"))
		mustCreate(t, s, input("Essays", "Orwell"))

		tests := []struct {
			name   string
			author string
			want   []string
		}{
			{"exact match", "George Orwell", []string{"Nineteen Eighty-Four", "Animal Farm"}},
			{"case-insensitive", "gEORGE oRWELL", []string{"Nineteen Eighty-Four", "Animal Farm"}},
			{"whole name only, not a substring", "Orwell", []string{"Essays"}},
			{"other author", "Aldous Huxley", []string{"Brave New World"}},
			{"unknown author", "Nobody", []string{}},
			{"no filter", "", []string{"Nineteen Eighty-Four", "Brave New World", "Animal Farm", "Essays"}},
		}
		for _, tt := range tests {
			t.Run(tt.name, func(t *testing.T) {
				if got := titles(mustList(t, s, tt.author)); !slices.Equal(got, tt.want) {
					t.Errorf("List(%q) titles = %v, want %v", tt.author, got, tt.want)
				}
			})
		}
	})
}

func TestUpdateReplacesEveryField(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		target := mustCreate(t, s, input("Old", "Old Author"))
		other := mustCreate(t, s, input("Bystander", "Someone Else"))

		replacement := book.Input{Title: "New", Author: "New Author"} // year and isbn reset
		updated, err := s.Update(t.Context(), target.ID, replacement)
		if err != nil {
			t.Fatalf("Update: %v", err)
		}
		if want := (book.Book{ID: target.ID, Input: replacement}); updated != want {
			t.Errorf("Update returned %+v, want %+v", updated, want)
		}

		got, err := s.Get(t.Context(), target.ID)
		if err != nil || got != updated {
			t.Errorf("Get after Update = %+v, %v; want %+v", got, err, updated)
		}
		if got, err := s.Get(t.Context(), other.ID); err != nil || got != other {
			t.Errorf("Update touched another book: %+v, %v; want %+v", got, err, other)
		}
	})
}

func TestUpdateMissingBook(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		_, err := s.Update(t.Context(), 42, input("Ghost", "Nobody"))
		if !errors.Is(err, book.ErrNotFound) {
			t.Errorf("Update error = %v, want book.ErrNotFound", err)
		}
		if got := mustList(t, s, ""); len(got) != 0 {
			t.Errorf("Update of a missing book created rows: %+v", got)
		}
	})
}

func TestDelete(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		keep := mustCreate(t, s, input("Keep", "A"))
		drop := mustCreate(t, s, input("Drop", "A"))

		if err := s.Delete(t.Context(), drop.ID); err != nil {
			t.Fatalf("Delete: %v", err)
		}
		if _, err := s.Get(t.Context(), drop.ID); !errors.Is(err, book.ErrNotFound) {
			t.Errorf("Get after Delete error = %v, want book.ErrNotFound", err)
		}
		if err := s.Delete(t.Context(), drop.ID); !errors.Is(err, book.ErrNotFound) {
			t.Errorf("second Delete error = %v, want book.ErrNotFound", err)
		}
		if got := mustList(t, s, ""); len(got) != 1 || got[0] != keep {
			t.Errorf("List after Delete = %+v, want only %+v", got, keep)
		}
	})
}

func TestIDsAreNeverReused(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		last := mustCreate(t, s, input("Last", "A"))
		if err := s.Delete(t.Context(), last.ID); err != nil {
			t.Fatalf("Delete: %v", err)
		}
		next := mustCreate(t, s, input("Next", "A"))
		if next.ID <= last.ID {
			t.Errorf("new id %d does not exceed the deleted id %d", next.ID, last.ID)
		}
	})
}

func TestDataSurvivesReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	first, err := store.Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	created := mustCreate(t, first, input("Durable", "Author"))
	if err := first.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	second := open(t, path) // reopening must not fail on the existing schema
	got, err := second.Get(t.Context(), created.ID)
	if err != nil || got != created {
		t.Errorf("Get after reopen = %+v, %v; want %+v", got, err, created)
	}
}

func TestMemoryDatabasesArePrivate(t *testing.T) {
	a, b := open(t, store.Memory), open(t, store.Memory)
	mustCreate(t, a, input("Only in a", "A"))
	if got := mustList(t, b, ""); len(got) != 0 {
		t.Errorf("second in-memory store sees %+v, want it empty", got)
	}
}

func TestOpenReportsUnusablePaths(t *testing.T) {
	dir := t.TempDir()
	file := filepath.Join(dir, "plain-file")
	if err := os.WriteFile(file, []byte("x"), 0o600); err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name string
		path string
		want string
	}{
		{"missing directory", filepath.Join(dir, "missing", "books.db"), "database directory"},
		{"parent is a file", filepath.Join(file, "books.db"), "database directory"},
		{"path is a directory", dir, "initialise database"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s, err := store.Open(tt.path)
			if err == nil {
				s.Close()
				t.Fatal("Open succeeded, want an error")
			}
			if !strings.Contains(err.Error(), tt.want) {
				t.Errorf("Open error = %q, want it to mention %q", err, tt.want)
			}
		})
	}
}

func TestOpenHandlesPathsWithURICharacters(t *testing.T) {
	names := []string{
		"plain.db",
		"with space.db",
		"question?mark.db",
		"hash#tag.db",
		"percent%20sign.db",
		"amp&equals=semi;colon.db",
		"ünïcödé.db",
	}
	for _, name := range names {
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), name)
			first, err := store.Open(path)
			if err != nil {
				t.Fatalf("Open: %v", err)
			}
			created := mustCreate(t, first, input("Kept", "A"))
			first.Close()

			// The file must sit exactly where it was asked for, not at some
			// URI-decoded variant of the path.
			if _, err := os.Stat(path); err != nil {
				t.Fatalf("database file is not at the requested path: %v", err)
			}
			second := open(t, path)
			if got, err := second.Get(t.Context(), created.ID); err != nil || got != created {
				t.Errorf("Get after reopen = %+v, %v; want %+v", got, err, created)
			}
		})
	}
}

func TestConcurrentUse(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		const writers, perWriter = 16, 10

		var wg sync.WaitGroup
		for w := range writers {
			wg.Go(func() {
				for i := range perWriter {
					author := fmt.Sprintf("writer-%d", w)
					if _, err := s.Create(t.Context(), input(fmt.Sprintf("%s-%d", author, i), author)); err != nil {
						t.Errorf("Create: %v", err)
					}
					// Interleave reads with the writes.
					if _, err := s.List(t.Context(), author); err != nil {
						t.Errorf("List: %v", err)
					}
				}
			})
		}
		wg.Wait()

		books := mustList(t, s, "")
		if len(books) != writers*perWriter {
			t.Fatalf("stored %d books, want %d", len(books), writers*perWriter)
		}
		seen := make(map[int64]bool)
		for _, b := range books {
			if seen[b.ID] {
				t.Fatalf("id %d was handed out twice", b.ID)
			}
			seen[b.ID] = true
		}
	})
}

func TestWaitsForLockHeldByAnotherConnection(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	s := open(t, path)

	// A second connection stands in for another process (say, the sqlite3
	// shell) that holds the write lock for a moment.
	other, err := sql.Open("sqlite", path)
	if err != nil {
		t.Fatal(err)
	}
	defer other.Close()
	conn, err := other.Conn(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	if _, err := conn.ExecContext(t.Context(), "BEGIN IMMEDIATE"); err != nil {
		t.Fatalf("taking the write lock: %v", err)
	}

	type outcome struct {
		err        error
		finishedAt time.Time
	}
	done := make(chan outcome, 1)
	go func() {
		_, err := s.Create(t.Context(), input("Patient", "Writer"))
		done <- outcome{err, time.Now()}
	}()

	time.Sleep(300 * time.Millisecond) // long enough for Create to run into the lock
	releasedAt := time.Now()
	if _, err := conn.ExecContext(t.Context(), "COMMIT"); err != nil {
		t.Fatalf("releasing the write lock: %v", err)
	}
	got := <-done
	if got.err != nil {
		t.Fatalf("Create while the database was locked: %v (it should have waited)", got.err)
	}
	if got.finishedAt.Before(releasedAt) {
		t.Errorf("Create finished %v before the lock was released, so it never waited for it",
			releasedAt.Sub(got.finishedAt))
	}
}

func TestQueriesAreParameterized(t *testing.T) {
	eachStore(t, func(t *testing.T, s *store.Store) {
		nasty := `x'); DROP TABLE books; --`
		created := mustCreate(t, s, book.Input{Title: nasty, Author: nasty})

		got, err := s.Get(t.Context(), created.ID)
		if err != nil || got.Title != nasty || got.Author != nasty {
			t.Fatalf("Get = %+v, %v; want the text stored verbatim", got, err)
		}
		if n := len(mustList(t, s, "")); n != 1 {
			t.Errorf("books table holds %d rows after the injection attempt, want 1", n)
		}
		if n := len(mustList(t, s, `' OR '1'='1`)); n != 0 {
			t.Errorf("injected author filter matched %d rows, want 0", n)
		}
		if n := len(mustList(t, s, nasty)); n != 1 {
			t.Errorf("filtering by the literal text matched %d rows, want 1", n)
		}
	})
}

func TestCancelledContextIsHonoured(t *testing.T) {
	s := openFile(t)
	ctx, cancel := context.WithCancel(t.Context())
	cancel()

	calls := map[string]func() error{
		"Create": func() error { _, err := s.Create(ctx, input("T", "A")); return err },
		"Get":    func() error { _, err := s.Get(ctx, 1); return err },
		"List":   func() error { _, err := s.List(ctx, ""); return err },
		"Update": func() error { _, err := s.Update(ctx, 1, input("T", "A")); return err },
		"Delete": func() error { return s.Delete(ctx, 1) },
		"Ping":   func() error { return s.Ping(ctx) },
	}
	for name, call := range calls {
		if err := call(); !errors.Is(err, context.Canceled) {
			t.Errorf("%s with a cancelled context returned %v, want context.Canceled", name, err)
		}
	}
}

func TestPingDetectsDamagedDatabase(t *testing.T) {
	t.Run("dropped table", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "books.db")
		s := open(t, path)
		if err := s.Ping(t.Context()); err != nil {
			t.Fatalf("Ping on a healthy database: %v", err)
		}

		other, err := sql.Open("sqlite", path)
		if err != nil {
			t.Fatal(err)
		}
		defer other.Close()
		if _, err := other.ExecContext(t.Context(), "DROP TABLE books"); err != nil {
			t.Fatalf("dropping the table: %v", err)
		}

		if err := s.Ping(t.Context()); err == nil || !strings.Contains(err.Error(), "no such table") {
			t.Errorf("Ping after the table was dropped = %v, want a \"no such table\" error", err)
		}
	})

	t.Run("file overwritten", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "books.db")
		s := open(t, path)
		mustCreate(t, s, input("Before", "The Damage"))

		garbage := strings.Repeat("this is not an SQLite database. ", 200)
		if err := os.WriteFile(path, []byte(garbage), 0o600); err != nil {
			t.Fatal(err)
		}

		if err := s.Ping(t.Context()); err == nil {
			t.Error("Ping succeeded although the database file was overwritten with garbage")
		}
	})
}

func TestPingAndClose(t *testing.T) {
	s, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Ping(t.Context()); err != nil {
		t.Errorf("Ping on an open store: %v", err)
	}
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	if err := s.Ping(t.Context()); err == nil {
		t.Error("Ping on a closed store succeeded, want an error")
	}
	if _, err := s.List(t.Context(), ""); err == nil {
		t.Error("List on a closed store succeeded, want an error")
	}
}
