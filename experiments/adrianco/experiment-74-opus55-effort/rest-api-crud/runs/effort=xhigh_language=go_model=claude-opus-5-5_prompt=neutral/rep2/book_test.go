package main

import (
	"strings"
	"testing"
	"time"
)

func intPtr(v int) *int       { return &v }
func strPtr(v string) *string { return &v }

func fixedNow() time.Time { return time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC) }

// invalidFields returns the keys of errs in a fixed field order.
func invalidFields(errs map[string]string) []string {
	var fields []string
	for _, k := range []string{"title", "author", "year", "isbn"} {
		if _, ok := errs[k]; ok {
			fields = append(fields, k)
		}
	}
	return fields
}

func TestBookInputValidate(t *testing.T) {
	tests := []struct {
		name      string
		in        BookInput
		wantErrs  []string // fields expected to be rejected, in title/author/year/isbn order
		wantTitle string
	}{
		{
			name:      "minimal valid",
			in:        BookInput{Title: "Dune", Author: "Frank Herbert"},
			wantTitle: "Dune",
		},
		{
			name:      "full valid with ISBN-13 and hyphens",
			in:        BookInput{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("978-0-441-17271-9")},
			wantTitle: "Dune",
		},
		{
			name:      "ISBN-10 with X check digit",
			in:        BookInput{Title: "T", Author: "A", ISBN: strPtr("0-8044-2957-X")},
			wantTitle: "T",
		},
		{
			name:      "surrounding whitespace is trimmed",
			in:        BookInput{Title: "  Dune  ", Author: " Frank Herbert "},
			wantTitle: "Dune",
		},
		{
			name:      "empty ISBN treated as absent",
			in:        BookInput{Title: "T", Author: "A", ISBN: strPtr("  ")},
			wantTitle: "T",
		},
		{
			name:      "next year allowed for forthcoming books",
			in:        BookInput{Title: "T", Author: "A", Year: intPtr(2027)},
			wantTitle: "T",
		},
		{
			name:     "missing title and author",
			in:       BookInput{},
			wantErrs: []string{"title", "author"},
		},
		{
			name:     "whitespace-only title",
			in:       BookInput{Title: "   ", Author: "A"},
			wantErrs: []string{"title"},
		},
		{
			name:     "title too long",
			in:       BookInput{Title: strings.Repeat("x", maxTitleLen+1), Author: "A"},
			wantErrs: []string{"title"},
		},
		{
			name:     "author too long",
			in:       BookInput{Title: "T", Author: strings.Repeat("é", maxAuthorLen+1)},
			wantErrs: []string{"author"},
		},
		{
			name:     "year zero",
			in:       BookInput{Title: "T", Author: "A", Year: intPtr(0)},
			wantErrs: []string{"year"},
		},
		{
			name:     "year too far in the future",
			in:       BookInput{Title: "T", Author: "A", Year: intPtr(2028)},
			wantErrs: []string{"year"},
		},
		{
			name:     "ISBN wrong length",
			in:       BookInput{Title: "T", Author: "A", ISBN: strPtr("12345")},
			wantErrs: []string{"isbn"},
		},
		{
			name:     "ISBN with letters",
			in:       BookInput{Title: "T", Author: "A", ISBN: strPtr("97804411727AB")},
			wantErrs: []string{"isbn"},
		},
		{
			name:     "X only allowed as ISBN-10 check digit",
			in:       BookInput{Title: "T", Author: "A", ISBN: strPtr("X804429570")},
			wantErrs: []string{"isbn"},
		},
		{
			name:     "all fields invalid are reported together",
			in:       BookInput{Year: intPtr(-5), ISBN: strPtr("nope")},
			wantErrs: []string{"title", "author", "year", "isbn"},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			book, errs := tc.in.Validate(fixedNow())
			if got := invalidFields(errs); strings.Join(got, ",") != strings.Join(tc.wantErrs, ",") {
				t.Fatalf("invalid fields = %v, want %v (errors: %v)", got, tc.wantErrs, errs)
			}
			if len(tc.wantErrs) > 0 {
				return
			}
			if book.Title != tc.wantTitle {
				t.Errorf("Title = %q, want %q", book.Title, tc.wantTitle)
			}
			if book.Author != strings.TrimSpace(tc.in.Author) {
				t.Errorf("Author = %q, want trimmed %q", book.Author, tc.in.Author)
			}
		})
	}
}

func TestValidateDoesNotAliasInput(t *testing.T) {
	year := 1965
	in := BookInput{Title: "Dune", Author: "Frank Herbert", Year: &year}
	book, errs := in.Validate(fixedNow())
	if errs != nil {
		t.Fatalf("unexpected errors: %v", errs)
	}
	year = 2000
	if *book.Year != 1965 {
		t.Errorf("book.Year changed with input to %d", *book.Year)
	}
}
