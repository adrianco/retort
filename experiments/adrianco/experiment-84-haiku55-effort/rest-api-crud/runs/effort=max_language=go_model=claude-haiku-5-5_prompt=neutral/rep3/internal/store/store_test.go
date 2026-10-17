package store

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"bookapi/internal/book"
)

func openTestStore(t *testing.T) (*Store, string) {
	t.Helper()
	path := filepath.Join(t.TempDir(), "books.db")
	st, err := Open(path)
	if err != nil {
		t.Fatalf("Open(%q): %v", path, err)
	}
	t.Cleanup(func() { st.Close() })
	return st, path
}

func TestCRUDRoundTrip(t *testing.T) {
	ctx := context.Background()
	st, _ := openTestStore(t)

	created, err := st.Create(ctx, book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create returned ID 0")
	}

	got, err := st.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Errorf("Get = %+v; want %+v", got, created)
	}

	// Update replaces every field, so the omitted ISBN is cleared.
	updated, err := st.Update(ctx, created.ID, book.Input{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	want := book.Book{ID: created.ID, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969}
	if updated != want {
		t.Errorf("Update = %+v; want %+v", updated, want)
	}
	if got, _ := st.Get(ctx, created.ID); got != want {
		t.Errorf("Get after Update = %+v; want %+v", got, want)
	}

	if err := st.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := st.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: err = %v; want ErrNotFound", err)
	}
}

func TestMissingBookReturnsErrNotFound(t *testing.T) {
	ctx := context.Background()
	st, _ := openTestStore(t)
	const missing = 424242

	if _, err := st.Get(ctx, missing); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v; want ErrNotFound", err)
	}
	if _, err := st.Update(ctx, missing, book.Input{Title: "x", Author: "y"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v; want ErrNotFound", err)
	}
	if err := st.Delete(ctx, missing); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v; want ErrNotFound", err)
	}
}

func TestListFiltersByAuthor(t *testing.T) {
	ctx := context.Background()
	st, _ := openTestStore(t)

	hobbit, _ := st.Create(ctx, book.Input{Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937})
	dune, _ := st.Create(ctx, book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	lotr, _ := st.Create(ctx, book.Input{Title: "The Silmarillion", Author: "J.R.R. Tolkien", Year: 1977})

	all, err := st.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if want := []book.Book{hobbit, dune, lotr}; !equalBooks(all, want) {
		t.Errorf("List(\"\") = %+v; want %+v (ordered by ID)", all, want)
	}

	tolkien, err := st.List(ctx, "tolkien")
	if err != nil {
		t.Fatalf("List(tolkien): %v", err)
	}
	if want := []book.Book{hobbit, lotr}; !equalBooks(tolkien, want) {
		t.Errorf("List(tolkien) = %+v; want %+v", tolkien, want)
	}

	herbert, err := st.List(ctx, "FRANK HERBERT")
	if err != nil {
		t.Fatalf("List(FRANK HERBERT): %v", err)
	}
	if want := []book.Book{dune}; !equalBooks(herbert, want) {
		t.Errorf("List(FRANK HERBERT) = %+v; want %+v", herbert, want)
	}

	none, err := st.List(ctx, "nobody")
	if err != nil {
		t.Fatalf("List(nobody): %v", err)
	}
	if none == nil || len(none) != 0 {
		t.Errorf("List(nobody) = %#v; want a non-nil empty slice", none)
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
	ctx := context.Background()
	st, path := openTestStore(t)

	created, err := st.Create(ctx, book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := st.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened, err := Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	t.Cleanup(func() { reopened.Close() })

	got, err := reopened.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("Get after reopen = %+v; want %+v", got, created)
	}
	if err := reopened.Ping(ctx); err != nil {
		t.Errorf("Ping: %v", err)
	}
}

func TestOpenUsesPathLiterally(t *testing.T) {
	// Inside a file: DSN, SQLite would read "?", "#" and "%" as URI syntax and
	// quietly write to a different file.
	dir := filepath.Join(t.TempDir(), "odd ?#% dir")
	if err := os.Mkdir(dir, 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	path := filepath.Join(dir, "books.db")

	st, err := Open(path)
	if err != nil {
		t.Fatalf("Open(%q): %v", path, err)
	}
	t.Cleanup(func() { st.Close() })

	if _, err := st.Create(context.Background(), book.Input{Title: "Dune", Author: "Frank Herbert"}); err != nil {
		t.Fatalf("Create: %v", err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Errorf("database was not created at %q: %v", path, err)
	}
}

func equalBooks(a, b []book.Book) bool {
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
