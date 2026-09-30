package books

import (
	"context"
	"errors"
	"path/filepath"
	"strings"
	"testing"
)

func newStore(t *testing.T) *Store {
	t.Helper()
	s, err := Open(MemoryPath)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestCreateAndGet(t *testing.T) {
	s, ctx := newStore(t), context.Background()

	created, err := s.Create(ctx, Input{Title: "  Dune ", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected created book (want trimmed title and an ID): %+v", created)
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Errorf("Get = %+v, want %+v", got, created)
	}
}

func TestIDsAreNotReused(t *testing.T) {
	s, ctx := newStore(t), context.Background()
	first, _ := s.Create(ctx, Input{Title: "A", Author: "X"})
	if err := s.Delete(ctx, first.ID); err != nil {
		t.Fatal(err)
	}
	second, _ := s.Create(ctx, Input{Title: "B", Author: "X"})
	if second.ID == first.ID {
		t.Errorf("ID %d reused after delete", second.ID)
	}
}

func TestValidation(t *testing.T) {
	tests := []struct {
		name   string
		in     Input
		fields []string
	}{
		{"missing title", Input{Author: "A"}, []string{"title"}},
		{"blank title", Input{Title: "   ", Author: "A"}, []string{"title"}},
		{"missing author", Input{Title: "T"}, []string{"author"}},
		{"both missing", Input{}, []string{"title", "author"}},
		{"negative year", Input{Title: "T", Author: "A", Year: -1}, []string{"year"}},
		{"year too large", Input{Title: "T", Author: "A", Year: MaxYear + 1}, []string{"year"}},
		{"title too long", Input{Title: strings.Repeat("x", MaxTitleLen+1), Author: "A"}, []string{"title"}},
		{"author too long", Input{Title: "T", Author: strings.Repeat("x", MaxAuthorLen+1)}, []string{"author"}},
		{"isbn too long", Input{Title: "T", Author: "A", ISBN: strings.Repeat("9", MaxISBNLen+1)}, []string{"isbn"}},
	}
	s, ctx := newStore(t), context.Background()
	existing, _ := s.Create(ctx, Input{Title: "Keep", Author: "Me"})

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			check := func(op string, err error) {
				t.Helper()
				var verr ValidationError
				if !errors.As(err, &verr) {
					t.Fatalf("%s: err = %v, want ValidationError", op, err)
				}
				if len(verr) != len(tc.fields) {
					t.Errorf("%s: fields = %v, want %v", op, verr, tc.fields)
				}
				for _, f := range tc.fields {
					if verr[f] == "" {
						t.Errorf("%s: no message for field %q in %v", op, f, verr)
					}
				}
			}
			_, err := s.Create(ctx, tc.in)
			check("Create", err)
			_, err = s.Update(ctx, existing.ID, tc.in)
			check("Update", err)
		})
	}

	if got, _ := s.List(ctx, ""); len(got) != 1 || got[0] != existing {
		t.Errorf("rejected input changed the store: %+v", got)
	}
}

func TestYearAndISBNAreOptional(t *testing.T) {
	s := newStore(t)
	b, err := s.Create(context.Background(), Input{Title: "T", Author: "A"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if b.Year != 0 || b.ISBN != "" {
		t.Errorf("got %+v, want zero year and empty isbn", b)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	s, ctx := newStore(t), context.Background()

	empty, err := s.List(ctx, "")
	if err != nil || empty == nil || len(empty) != 0 {
		t.Fatalf("empty List = %#v, %v; want non-nil empty slice", empty, err)
	}

	for _, in := range []Input{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Persuasion", Author: "Jane Austen"},
	} {
		if _, err := s.Create(ctx, in); err != nil {
			t.Fatal(err)
		}
	}

	all, _ := s.List(ctx, "")
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	for _, author := range []string{"Jane Austen", "jane austen"} {
		got, err := s.List(ctx, author)
		if err != nil {
			t.Fatal(err)
		}
		if len(got) != 2 || got[0].Title != "Emma" || got[1].Title != "Persuasion" {
			t.Errorf("List(%q) = %+v, want Emma then Persuasion", author, got)
		}
	}

	if got, _ := s.List(ctx, "Austen"); len(got) != 0 {
		t.Errorf("partial author matched: %+v", got)
	}
	// The filter is a bound parameter, not SQL.
	if got, _ := s.List(ctx, "x' OR '1'='1"); len(got) != 0 {
		t.Errorf("injection-like filter matched: %+v", got)
	}
}

func TestUpdate(t *testing.T) {
	s, ctx := newStore(t), context.Background()
	b, _ := s.Create(ctx, Input{Title: "Old", Author: "A", Year: 1990, ISBN: "1"})

	updated, err := s.Update(ctx, b.ID, Input{Title: "New", Author: "B", Year: 2000, ISBN: "2"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	want := Book{ID: b.ID, Title: "New", Author: "B", Year: 2000, ISBN: "2"}
	if updated != want {
		t.Errorf("Update = %+v, want %+v", updated, want)
	}
	if got, _ := s.Get(ctx, b.ID); got != want {
		t.Errorf("stored = %+v, want %+v", got, want)
	}

	// Re-saving identical values must still count as found.
	if _, err := s.Update(ctx, b.ID, Input{Title: "New", Author: "B", Year: 2000, ISBN: "2"}); err != nil {
		t.Errorf("no-op Update: %v", err)
	}
}

func TestNotFound(t *testing.T) {
	s, ctx := newStore(t), context.Background()
	valid := Input{Title: "T", Author: "A"}

	if _, err := s.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: %v, want ErrNotFound", err)
	}
	if _, err := s.Update(ctx, 42, valid); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: %v, want ErrNotFound", err)
	}
}

func TestDelete(t *testing.T) {
	s, ctx := newStore(t), context.Background()
	b, _ := s.Create(ctx, Input{Title: "T", Author: "A"})

	if err := s.Delete(ctx, b.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, b.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, b.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("second Delete: %v, want ErrNotFound", err)
	}
}

func TestPersistsOnDisk(t *testing.T) {
	// A path with URI-special characters must still be treated literally.
	path := filepath.Join(t.TempDir(), "my books?#1.db")
	ctx := context.Background()

	s, err := Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	b, err := s.Create(ctx, Input{Title: "Persistent", Author: "A"})
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}

	s, err = Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer s.Close()
	got, err := s.Get(ctx, b.ID)
	if err != nil || got != b {
		t.Errorf("after reopen Get = %+v, %v; want %+v", got, err, b)
	}
}

func TestPingAfterClose(t *testing.T) {
	s := newStore(t)
	if err := s.Ping(context.Background()); err != nil {
		t.Fatalf("Ping: %v", err)
	}
	s.Close()
	if err := s.Ping(context.Background()); err == nil {
		t.Error("Ping succeeded on a closed store")
	}
}
