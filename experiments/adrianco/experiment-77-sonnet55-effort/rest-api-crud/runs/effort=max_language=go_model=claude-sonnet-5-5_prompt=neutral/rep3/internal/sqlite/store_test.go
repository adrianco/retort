package sqlite_test

import (
	"context"
	"database/sql"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"

	"bookapi/internal/book"
	"bookapi/internal/sqlite"
)

var ctx = context.Background()

func ptr[T any](v T) *T { return &v }

func newStore(t *testing.T) *sqlite.Store {
	t.Helper()
	s, err := sqlite.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func mustCreate(t *testing.T, s *sqlite.Store, in book.Input) book.Book {
	t.Helper()
	b, err := s.Create(ctx, in)
	if err != nil {
		t.Fatalf("Create(%+v): %v", in, err)
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

func TestCreateAndGet(t *testing.T) {
	s := newStore(t)

	created := mustCreate(t, s, book.Input{
		Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("9780441172719"),
	})
	if created.ID < 1 {
		t.Fatalf("Create returned ID %d, want a positive ID", created.ID)
	}
	want := book.Book{ID: created.ID, Input: book.Input{
		Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("9780441172719"),
	}}
	if !reflect.DeepEqual(created, want) {
		t.Errorf("Create = %+v, want %+v", created, want)
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if !reflect.DeepEqual(got, created) {
		t.Errorf("Get = %+v, want %+v", got, created)
	}
}

func TestOptionalFieldsRoundTrip(t *testing.T) {
	s := newStore(t)

	absent := mustCreate(t, s, book.Input{Title: "No extras", Author: "A"})
	zeroYear := mustCreate(t, s, book.Input{Title: "Year zero", Author: "A", Year: ptr(0)})

	got, err := s.Get(ctx, absent.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Year != nil || got.ISBN != nil {
		t.Errorf("omitted year/isbn came back as %v/%v, want nil/nil", got.Year, got.ISBN)
	}

	// A year of 0 is a real value and must not be confused with "not provided".
	got, err = s.Get(ctx, zeroYear.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Year == nil || *got.Year != 0 {
		t.Errorf("year 0 came back as %v, want a pointer to 0", got.Year)
	}
}

func TestGetNotFound(t *testing.T) {
	s := newStore(t)
	if _, err := s.Get(ctx, 42); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Get(42) error = %v, want book.ErrNotFound", err)
	}
}

func TestIDsAreNeverReused(t *testing.T) {
	s := newStore(t)
	first := mustCreate(t, s, book.Input{Title: "One", Author: "A"})
	second := mustCreate(t, s, book.Input{Title: "Two", Author: "A"})
	if second.ID <= first.ID {
		t.Fatalf("IDs %d then %d are not increasing", first.ID, second.ID)
	}

	if err := s.Delete(ctx, second.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	third := mustCreate(t, s, book.Input{Title: "Three", Author: "A"})
	if third.ID <= second.ID {
		t.Errorf("ID %d was reused or went backwards after deleting %d", third.ID, second.ID)
	}
}

func TestListEmpty(t *testing.T) {
	s := newStore(t)
	books, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(books) != 0 {
		t.Errorf("List on an empty store = %v, want no books", books)
	}
}

func TestListOrderAndAuthorFilter(t *testing.T) {
	s := newStore(t)
	mustCreate(t, s, book.Input{Title: "Dune", Author: "Frank Herbert"})
	mustCreate(t, s, book.Input{Title: "Emma", Author: "Jane Austen"})
	mustCreate(t, s, book.Input{Title: "Persuasion", Author: "jane austen"})
	mustCreate(t, s, book.Input{Title: "Children of Dune", Author: "Frank Herbert"})

	tests := []struct {
		name   string
		author string
		want   []string
	}{
		{"no filter returns everything in insertion order", "", []string{"Dune", "Emma", "Persuasion", "Children of Dune"}},
		{"exact author", "Frank Herbert", []string{"Dune", "Children of Dune"}},
		{"ignores case", "JANE AUSTEN", []string{"Emma", "Persuasion"}},
		{"is not a substring match", "Austen", nil},
		{"unknown author", "Nobody", nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			books, err := s.List(ctx, tt.author)
			if err != nil {
				t.Fatalf("List(%q): %v", tt.author, err)
			}
			if got := titles(books); !reflect.DeepEqual(got, tt.want) && (len(got) != 0 || len(tt.want) != 0) {
				t.Errorf("List(%q) titles = %v, want %v", tt.author, got, tt.want)
			}
		})
	}
}

// The filter is an equality test, so LIKE wildcards and SQL syntax in the value
// are just characters.
func TestListAuthorFilterTreatsTheValueLiterally(t *testing.T) {
	s := newStore(t)
	mustCreate(t, s, book.Input{Title: "Wildcard", Author: "100% Pure"})
	mustCreate(t, s, book.Input{Title: "Underscore", Author: "A_B"})
	mustCreate(t, s, book.Input{Title: "Decoy", Author: "AxB"})
	mustCreate(t, s, book.Input{Title: "Quote", Author: "O'Brien"})

	tests := []struct {
		author string
		want   []string
	}{
		{"%", nil},
		{"100% Pure", []string{"Wildcard"}},
		{"A_B", []string{"Underscore"}},
		{"O'Brien", []string{"Quote"}},
		{"' OR '1'='1", nil},
		{"x'; DROP TABLE books; --", nil},
	}
	for _, tt := range tests {
		books, err := s.List(ctx, tt.author)
		if err != nil {
			t.Fatalf("List(%q): %v", tt.author, err)
		}
		if got := titles(books); len(got) != len(tt.want) || (len(got) > 0 && !reflect.DeepEqual(got, tt.want)) {
			t.Errorf("List(%q) titles = %v, want %v", tt.author, got, tt.want)
		}
	}

	if all, err := s.List(ctx, ""); err != nil || len(all) != 4 {
		t.Errorf("the table was damaged: %d books, err %v, want 4 books", len(all), err)
	}
}

func TestUpdate(t *testing.T) {
	s := newStore(t)
	target := mustCreate(t, s, book.Input{Title: "Old", Author: "Old Author", Year: ptr(1900), ISBN: ptr("111")})
	other := mustCreate(t, s, book.Input{Title: "Other", Author: "Someone", Year: ptr(2000)})

	// Update replaces the whole book, so the omitted year and ISBN are cleared.
	updated, err := s.Update(ctx, target.ID, book.Input{Title: "New", Author: "New Author"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	want := book.Book{ID: target.ID, Input: book.Input{Title: "New", Author: "New Author"}}
	if !reflect.DeepEqual(updated, want) {
		t.Errorf("Update = %+v, want %+v", updated, want)
	}

	got, err := s.Get(ctx, target.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("Get after Update = %+v, want %+v", got, want)
	}
	if untouched, _ := s.Get(ctx, other.ID); !reflect.DeepEqual(untouched, other) {
		t.Errorf("Update changed another book: %+v, want %+v", untouched, other)
	}
}

func TestUpdateNotFound(t *testing.T) {
	s := newStore(t)
	_, err := s.Update(ctx, 7, book.Input{Title: "T", Author: "A"})
	if !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Update of a missing book error = %v, want book.ErrNotFound", err)
	}
	if books, _ := s.List(ctx, ""); len(books) != 0 {
		t.Errorf("Update of a missing book created %v", books)
	}
}

func TestDelete(t *testing.T) {
	s := newStore(t)
	doomed := mustCreate(t, s, book.Input{Title: "Doomed", Author: "A"})
	kept := mustCreate(t, s, book.Input{Title: "Kept", Author: "A"})

	if err := s.Delete(ctx, doomed.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, doomed.ID); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Get after Delete error = %v, want book.ErrNotFound", err)
	}
	if _, err := s.Get(ctx, kept.ID); err != nil {
		t.Errorf("Delete removed an unrelated book: %v", err)
	}
	if err := s.Delete(ctx, doomed.ID); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("second Delete error = %v, want book.ErrNotFound", err)
	}
}

func TestDataSurvivesReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	s, err := sqlite.Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	first := mustCreate(t, s, book.Input{Title: "Persistent", Author: "A", Year: ptr(2001)})
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	s, err = sqlite.Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer s.Close()

	got, err := s.Get(ctx, first.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if !reflect.DeepEqual(got, first) {
		t.Errorf("after reopen = %+v, want %+v", got, first)
	}
	if next := mustCreate(t, s, book.Input{Title: "Next", Author: "A"}); next.ID <= first.ID {
		t.Errorf("ID after reopen = %d, want more than %d", next.ID, first.ID)
	}
}

// The database path comes from a flag or environment variable, so characters
// that mean something in a URI or DSN must be treated as part of the file name.
func TestOpenTreatsPathAsLiteralFileName(t *testing.T) {
	names := []string{
		"plain.db",
		"with space.db",
		"hash#tag.db",
		"percent%20sign.db",
		"question?mark.db",
		"amp&ersand.db",
		"unicode-é.db",
		"injected.db?mode=ro&_pragma=query_only(1)", // must not be read as DSN parameters
	}
	for _, name := range names {
		t.Run(name, func(t *testing.T) {
			dir := t.TempDir()
			s, err := sqlite.Open(filepath.Join(dir, name))
			if err != nil {
				t.Fatalf("Open: %v", err)
			}
			mustCreate(t, s, book.Input{Title: "T", Author: "A"}) // fails if a DSN parameter made it read-only
			if err := s.Close(); err != nil {
				t.Fatalf("Close: %v", err)
			}

			entries, err := os.ReadDir(dir)
			if err != nil {
				t.Fatal(err)
			}
			if len(entries) != 1 || entries[0].Name() != name {
				var got []string
				for _, e := range entries {
					got = append(got, e.Name())
				}
				t.Errorf("directory holds %q, want exactly [%q]", got, name)
			}
		})
	}
}

// A path with two leading slashes is still one absolute path; it must not be
// mistaken for the "//host/path" form of a URI.
func TestOpenAcceptsAnAbsolutePathWithLeadingDoubleSlash(t *testing.T) {
	dir := t.TempDir()
	s, err := sqlite.Open("/" + filepath.Join(dir, "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	mustCreate(t, s, book.Input{Title: "T", Author: "A"})
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, "books.db")); err != nil {
		t.Errorf("the database was not created where the path points: %v", err)
	}
}

// Another connection to the same file (for instance the sqlite3 shell) may hold
// a lock for a moment. A write must wait for it rather than fail at once with
// "database is locked".
func TestWritesWaitForALockHeldByAnotherConnection(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	s, err := sqlite.Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer s.Close()

	other, err := sql.Open("sqlite", path)
	if err != nil {
		t.Fatal(err)
	}
	defer other.Close()
	holder, err := other.Conn(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer holder.Close()
	if _, err := holder.ExecContext(ctx, "BEGIN EXCLUSIVE"); err != nil {
		t.Fatalf("take the lock: %v", err)
	}

	created := make(chan error, 1)
	go func() {
		_, err := s.Create(ctx, book.Input{Title: "T", Author: "A"})
		created <- err
	}()

	select {
	case err := <-created:
		t.Fatalf("Create returned (%v) while another connection held the lock; it should have waited", err)
	case <-time.After(300 * time.Millisecond):
	}

	if _, err := holder.ExecContext(ctx, "COMMIT"); err != nil {
		t.Fatalf("release the lock: %v", err)
	}
	select {
	case err := <-created:
		if err != nil {
			t.Errorf("Create after the lock was released: %v", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("Create did not complete after the lock was released")
	}
}

func TestOpenInMemory(t *testing.T) {
	a, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer a.Close()
	b, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer b.Close()

	created := mustCreate(t, a, book.Input{Title: "Ephemeral", Author: "A"})
	if _, err := a.Get(ctx, created.ID); err != nil {
		t.Errorf("Get from the same in-memory store: %v", err)
	}
	if books, _ := b.List(ctx, ""); len(books) != 0 {
		t.Errorf("a second in-memory store sees %v, want it isolated", books)
	}
}

func TestOpenErrors(t *testing.T) {
	if _, err := sqlite.Open(""); err == nil {
		t.Error("Open(\"\") succeeded, want an error")
	}

	missing := filepath.Join(t.TempDir(), "no-such-dir", "books.db")
	_, err := sqlite.Open(missing)
	if err == nil {
		t.Fatal("Open in a missing directory succeeded, want an error")
	}
	if !strings.Contains(err.Error(), missing) {
		t.Errorf("error %q does not mention the path %q", err, missing)
	}
}

// The schema rejects blank titles and authors even if a caller skips validation.
func TestSchemaRejectsBlankRequiredFields(t *testing.T) {
	s := newStore(t)
	for _, in := range []book.Input{
		{Title: "", Author: "A"},
		{Title: "   ", Author: "A"},
		{Title: "T", Author: ""},
		{Title: "\x00x", Author: "A"}, // SQLite's length() stops at the NUL, so this looks empty
	} {
		if _, err := s.Create(ctx, in); err == nil {
			t.Errorf("Create(%+v) succeeded, want the schema to reject it", in)
		}
	}
	if books, _ := s.List(ctx, ""); len(books) != 0 {
		t.Errorf("rejected books were stored: %v", books)
	}
}

// Concurrent requests share one connection, so none may fail with SQLITE_BUSY
// and an in-memory database must stay one database for all of them.
func TestConcurrentCreates(t *testing.T) {
	paths := map[string]string{
		"file":   filepath.Join(t.TempDir(), "books.db"),
		"memory": ":memory:",
	}
	for name, path := range paths {
		t.Run(name, func(t *testing.T) {
			s, err := sqlite.Open(path)
			if err != nil {
				t.Fatalf("Open: %v", err)
			}
			defer s.Close()

			const workers, perWorker = 16, 25
			var wg sync.WaitGroup
			errs := make(chan error, workers*perWorker)
			for w := 0; w < workers; w++ {
				wg.Add(1)
				go func() {
					defer wg.Done()
					for i := 0; i < perWorker; i++ {
						if _, err := s.Create(ctx, book.Input{Title: "T", Author: "A"}); err != nil {
							errs <- err
						}
					}
				}()
			}
			wg.Wait()
			close(errs)
			for err := range errs {
				t.Errorf("concurrent Create: %v", err)
			}

			books, err := s.List(ctx, "")
			if err != nil {
				t.Fatalf("List: %v", err)
			}
			if len(books) != workers*perWorker {
				t.Errorf("stored %d books, want %d", len(books), workers*perWorker)
			}
		})
	}
}

func TestCanceledContext(t *testing.T) {
	s := newStore(t)
	canceled, cancel := context.WithCancel(ctx)
	cancel()

	if _, err := s.Create(canceled, book.Input{Title: "T", Author: "A"}); !errors.Is(err, context.Canceled) {
		t.Errorf("Create with a canceled context error = %v, want context.Canceled", err)
	}
	if books, _ := s.List(ctx, ""); len(books) != 0 {
		t.Errorf("a canceled Create stored %v", books)
	}
}

func TestPingAndClose(t *testing.T) {
	s := newStore(t)
	if err := s.Ping(ctx); err != nil {
		t.Errorf("Ping on an open store: %v", err)
	}
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	if err := s.Ping(ctx); err == nil {
		t.Error("Ping on a closed store succeeded, want an error")
	}
	if _, err := s.List(ctx, ""); err == nil {
		t.Error("List on a closed store succeeded, want an error")
	}
}

// A broken database must surface as an error, never as "book not found", which
// the API would present to clients as a 404.
func TestDatabaseFailuresAreNotReportedAsNotFound(t *testing.T) {
	s := newStore(t)
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	in := book.Input{Title: "T", Author: "A"}
	calls := map[string]func() error{
		"Create": func() error { _, err := s.Create(ctx, in); return err },
		"Get":    func() error { _, err := s.Get(ctx, 1); return err },
		"List":   func() error { _, err := s.List(ctx, ""); return err },
		"Update": func() error { _, err := s.Update(ctx, 1, in); return err },
		"Delete": func() error { return s.Delete(ctx, 1) },
	}
	for name, call := range calls {
		err := call()
		if err == nil {
			t.Errorf("%s on a closed store succeeded, want an error", name)
		} else if errors.Is(err, book.ErrNotFound) {
			t.Errorf("%s on a closed store returned ErrNotFound: %v", name, err)
		}
	}
}
