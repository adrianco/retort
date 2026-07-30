package main

import (
	"slices"
	"strings"
	"testing"
	"time"
)

// reference is the clock every validation test runs against, so the year
// bound ("current year + 1") does not drift with the wall clock.
var reference = time.Date(2026, time.July, 29, 12, 0, 0, 0, time.UTC)

func strPtr(s string) *string { return &s }
func intPtr(n int) *int       { return &n }

func TestValidateAcceptsAndNormalizes(t *testing.T) {
	in := BookInput{
		Title:  strPtr("  The Go Programming Language  "),
		Author: strPtr("\tAlan A. A. Donovan\n"),
		Year:   intPtr(2015),
		ISBN:   strPtr("978-0-13-419044-0"),
	}

	book, errs := in.Validate(reference)
	if len(errs) != 0 {
		t.Fatalf("Validate() returned errors for valid input: %+v", errs)
	}
	if book.Title != "The Go Programming Language" {
		t.Errorf("Title = %q, want surrounding whitespace trimmed", book.Title)
	}
	if book.Author != "Alan A. A. Donovan" {
		t.Errorf("Author = %q, want surrounding whitespace trimmed", book.Author)
	}
	if book.Year == nil || *book.Year != 2015 {
		t.Errorf("Year = %v, want 2015", book.Year)
	}
	if book.ISBN != "9780134190440" {
		t.Errorf("ISBN = %q, want separators stripped", book.ISBN)
	}
}

func TestValidateOptionalFields(t *testing.T) {
	// year and isbn are optional in every form a client might omit them.
	for _, in := range []BookInput{
		{Title: strPtr("Dune"), Author: strPtr("Frank Herbert")},
		{Title: strPtr("Dune"), Author: strPtr("Frank Herbert"), Year: nil, ISBN: nil},
		{Title: strPtr("Dune"), Author: strPtr("Frank Herbert"), ISBN: strPtr("")},
		{Title: strPtr("Dune"), Author: strPtr("Frank Herbert"), ISBN: strPtr("   ")},
	} {
		book, errs := in.Validate(reference)
		if len(errs) != 0 {
			t.Fatalf("Validate(%+v) returned errors: %+v", in, errs)
		}
		if book.Year != nil {
			t.Errorf("Year = %v, want nil", *book.Year)
		}
		if book.ISBN != "" {
			t.Errorf("ISBN = %q, want empty", book.ISBN)
		}
	}
}

func TestValidateRejects(t *testing.T) {
	longTitle := strings.Repeat("t", maxTitleLen+1)
	longAuthor := strings.Repeat("a", maxAuthorLen+1)

	tests := []struct {
		name       string
		in         BookInput
		wantFields []string
	}{
		{
			name:       "title missing",
			in:         BookInput{Author: strPtr("Frank Herbert")},
			wantFields: []string{"title"},
		},
		{
			name:       "author missing",
			in:         BookInput{Title: strPtr("Dune")},
			wantFields: []string{"author"},
		},
		{
			name:       "both missing",
			in:         BookInput{},
			wantFields: []string{"title", "author"},
		},
		{
			name:       "title blank",
			in:         BookInput{Title: strPtr("   "), Author: strPtr("Frank Herbert")},
			wantFields: []string{"title"},
		},
		{
			name:       "author blank",
			in:         BookInput{Title: strPtr("Dune"), Author: strPtr("")},
			wantFields: []string{"author"},
		},
		{
			name:       "title too long",
			in:         BookInput{Title: strPtr(longTitle), Author: strPtr("Frank Herbert")},
			wantFields: []string{"title"},
		},
		{
			name:       "author too long",
			in:         BookInput{Title: strPtr("Dune"), Author: strPtr(longAuthor)},
			wantFields: []string{"author"},
		},
		{
			name:       "year before minimum",
			in:         BookInput{Title: strPtr("Dune"), Author: strPtr("Frank Herbert"), Year: intPtr(12)},
			wantFields: []string{"year"},
		},
		{
			name:       "year too far in the future",
			in:         BookInput{Title: strPtr("Dune"), Author: strPtr("Frank Herbert"), Year: intPtr(reference.Year() + 2)},
			wantFields: []string{"year"},
		},
		{
			name:       "isbn checksum wrong",
			in:         BookInput{Title: strPtr("Dune"), Author: strPtr("Frank Herbert"), ISBN: strPtr("978-0-13-419044-1")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "every field bad at once",
			in:         BookInput{Title: strPtr(""), Author: strPtr(" "), Year: intPtr(0), ISBN: strPtr("nope")},
			wantFields: []string{"title", "author", "year", "isbn"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			book, errs := tt.in.Validate(reference)
			if got := fieldNames(errs); !slices.Equal(got, tt.wantFields) {
				t.Fatalf("Validate() reported fields %v, want %v (errors: %+v)", got, tt.wantFields, errs)
			}
			if book != (Book{}) {
				t.Errorf("Validate() returned %+v alongside errors, want zero Book", book)
			}
			for _, e := range errs {
				if e.Message == "" {
					t.Errorf("field %q has an empty message", e.Field)
				}
			}
		})
	}
}

// The upper year bound follows the clock, so a book catalogued for next year
// is accepted and the year after that is not.
func TestValidateYearBoundsFollowClock(t *testing.T) {
	base := BookInput{Title: strPtr("Dune"), Author: strPtr("Frank Herbert")}

	for _, tt := range []struct {
		year int
		ok   bool
	}{
		{minYear - 1, false},
		{minYear, true},
		{reference.Year(), true},
		{reference.Year() + 1, true},
		{reference.Year() + 2, false},
	} {
		in := base
		in.Year = intPtr(tt.year)
		_, errs := in.Validate(reference)
		if ok := len(errs) == 0; ok != tt.ok {
			t.Errorf("Validate(year=%d) accepted = %v, want %v", tt.year, ok, tt.ok)
		}
	}
}

func TestNormalizeISBN(t *testing.T) {
	tests := []struct {
		in   string
		want string
		ok   bool
	}{
		// ISBN-10, with and without the separators it may be written with.
		{"0306406152", "0306406152", true},
		{"0-306-40615-2", "0306406152", true},
		{"0 306 40615 2", "0306406152", true},
		// Check digit 10 is written X, in either case.
		{"043942089X", "043942089X", true},
		{"043942089x", "043942089X", true},
		// ISBN-13.
		{"9780134190440", "9780134190440", true},
		{"978-0-13-419044-0", "9780134190440", true},
		{"9783161484100", "9783161484100", true},

		{"", "", false},
		{"0306406153", "", false},       // ISBN-10 checksum off by one
		{"9780134190441", "", false},    // ISBN-13 checksum off by one
		{"03064061", "", false},         // too short
		{"03064061521", "", false},      // 11 digits is neither length
		{"978013419044", "", false},     // 12 digits
		{"97801341904400", "", false},   // 14 digits
		{"X306406152", "", false},       // X outside the check position
		{"978013419044X", "", false},    // X is not legal in an ISBN-13
		{"0306406152 extra", "", false}, // stray letters
		{"0—306—40615—2", "", false},    // em dashes are not separators
	}

	for _, tt := range tests {
		got, ok := NormalizeISBN(tt.in)
		if ok != tt.ok || got != tt.want {
			t.Errorf("NormalizeISBN(%q) = (%q, %v), want (%q, %v)", tt.in, got, ok, tt.want, tt.ok)
		}
	}
}

func fieldNames(errs []FieldError) []string {
	names := make([]string, len(errs))
	for i, e := range errs {
		names[i] = e.Field
	}
	return names
}
