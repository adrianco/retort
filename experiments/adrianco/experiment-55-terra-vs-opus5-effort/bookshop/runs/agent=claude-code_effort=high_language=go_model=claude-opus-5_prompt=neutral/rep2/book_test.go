package main

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestValidateISBN(t *testing.T) {
	tests := []struct {
		raw   string
		valid bool
	}{
		{"0306406152", true},         // ISBN-10
		{"0-306-40615-2", true},      // ISBN-10 with hyphens
		{"0 306 40615 2", true},      // ISBN-10 with spaces
		{"080442957X", true},         // ISBN-10 with X check digit
		{"080442957x", true},         // lowercase x is normalized
		{"9780134190440", true},      // ISBN-13
		{"978-0-13-419044-0", true},  // ISBN-13 with hyphens
		{"0306406153", false},        // bad ISBN-10 check digit
		{"9780134190441", false},     // bad ISBN-13 check digit
		{"X306406152", false},        // X outside the check position
		{"03064061", false},          // too short
		{"97801341904400", false},    // too long
		{"abcdefghij", false},        // not digits
		{"978-0-13-41904a-0", false}, // stray letter
	}

	for _, tc := range tests {
		t.Run(tc.raw, func(t *testing.T) {
			if got := validISBN(normalizeISBN(tc.raw)); got != tc.valid {
				t.Errorf("validISBN(%q) = %v, want %v", tc.raw, got, tc.valid)
			}
		})
	}
}

func TestBookInputValidate(t *testing.T) {
	nextYear := time.Now().UTC().Year() + 1

	tests := []struct {
		name        string
		in          BookInput
		wantProblem string // empty means the input should be accepted
	}{
		{
			name: "minimal valid input",
			in:   BookInput{Title: "Ulysses", Author: "James Joyce"},
		},
		{
			name: "year zero means unknown",
			in:   BookInput{Title: "Ulysses", Author: "James Joyce", Year: 0},
		},
		{
			name: "forthcoming title is allowed",
			in:   BookInput{Title: "Ulysses", Author: "James Joyce", Year: nextYear},
		},
		{
			name:        "year beyond next year",
			in:          BookInput{Title: "Ulysses", Author: "James Joyce", Year: nextYear + 1},
			wantProblem: "year",
		},
		{
			name:        "year before printing",
			in:          BookInput{Title: "Ulysses", Author: "James Joyce", Year: 900},
			wantProblem: "year",
		},
		{
			name:        "empty title",
			in:          BookInput{Author: "James Joyce"},
			wantProblem: "title",
		},
		{
			name:        "empty author",
			in:          BookInput{Title: "Ulysses"},
			wantProblem: "author",
		},
		{
			name:        "overlong title",
			in:          BookInput{Title: string(make([]byte, 501)), Author: "James Joyce"},
			wantProblem: "title",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			in := tc.in
			in.Normalize()
			problems := in.Validate()

			if tc.wantProblem == "" {
				if len(problems) != 0 {
					t.Fatalf("problems = %v, want none", problems)
				}
				return
			}
			if _, ok := problems[tc.wantProblem]; !ok {
				t.Fatalf("problems = %v, want an entry for %q", problems, tc.wantProblem)
			}
		})
	}
}

func TestNormalizeTrimsWhitespace(t *testing.T) {
	in := BookInput{Title: "\t Neuromancer \n", Author: "  William Gibson  ", ISBN: " 0-441-56956-0 "}
	in.Normalize()

	if in.Title != "Neuromancer" {
		t.Errorf("Title = %q, want %q", in.Title, "Neuromancer")
	}
	if in.Author != "William Gibson" {
		t.Errorf("Author = %q, want %q", in.Author, "William Gibson")
	}
	if in.ISBN != "0441569560" {
		t.Errorf("ISBN = %q, want %q", in.ISBN, "0441569560")
	}
}

func TestStoreNotFoundErrors(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	ctx := context.Background()

	if _, err := store.Get(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get on empty store: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, 1, BookInput{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update on empty store: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete on empty store: err = %v, want ErrNotFound", err)
	}
}

func TestStoreDuplicateISBN(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	ctx := context.Background()
	first, err := store.Create(ctx, BookInput{Title: "First", Author: "A", ISBN: "0306406152"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	if _, err := store.Create(ctx, BookInput{Title: "Second", Author: "B", ISBN: "0306406152"}); !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("duplicate Create: err = %v, want ErrDuplicateISBN", err)
	}

	second, err := store.Create(ctx, BookInput{Title: "Second", Author: "B", ISBN: "080442957X"})
	if err != nil {
		t.Fatalf("Create with distinct isbn: %v", err)
	}
	if _, err := store.Update(ctx, second.ID, BookInput{Title: "Second", Author: "B", ISBN: first.ISBN}); !errors.Is(err, ErrDuplicateISBN) {
		t.Errorf("Update onto taken isbn: err = %v, want ErrDuplicateISBN", err)
	}
}

// TestStorePersistsAcrossReopen proves data really lands on disk rather than
// living only in the process.
func TestStorePersistsAcrossReopen(t *testing.T) {
	path := t.TempDir() + "/books.db"
	ctx := context.Background()

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created, err := store.Create(ctx, BookInput{Title: "Persisted", Author: "Author", Year: 2020})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	reopened, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer reopened.Close()

	got, err := reopened.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("got %+v, want %+v", got, created)
	}
}
