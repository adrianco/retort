package main

import (
	"maps"
	"reflect"
	"slices"
	"strings"
	"testing"
	"time"
)

// fixedNow pins the clock so the year bounds are the same on every run.
var fixedNow = time.Date(2026, time.October, 17, 12, 0, 0, 0, time.UTC)

func intPtr(v int) *int       { return &v }
func strPtr(s string) *string { return &s }

func TestBookInputToBook(t *testing.T) {
	tests := []struct {
		name       string
		in         bookInput
		wantFields []string // fields expected to fail validation; nil if valid
		want       Book     // compared only when the input is valid
	}{
		{
			name: "minimal valid book",
			in:   bookInput{Title: "Dune", Author: "Frank Herbert"},
			want: Book{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name: "title and author are trimmed",
			in:   bookInput{Title: "  Dune  ", Author: "\tFrank Herbert\n"},
			want: Book{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name:       "missing title",
			in:         bookInput{Author: "Frank Herbert"},
			wantFields: []string{"title"},
		},
		{
			name:       "whitespace-only title",
			in:         bookInput{Title: "   ", Author: "Frank Herbert"},
			wantFields: []string{"title"},
		},
		{
			name:       "missing author",
			in:         bookInput{Title: "Dune"},
			wantFields: []string{"author"},
		},
		{
			name:       "missing title and author are both reported",
			in:         bookInput{Year: intPtr(1965)},
			wantFields: []string{"author", "title"},
		},
		{
			name:       "title longer than the limit",
			in:         bookInput{Title: strings.Repeat("a", maxTextLength+1), Author: "A"},
			wantFields: []string{"title"},
		},
		{
			name: "title at the limit is accepted",
			in:   bookInput{Title: strings.Repeat("é", maxTextLength), Author: "A"},
			want: Book{Title: strings.Repeat("é", maxTextLength), Author: "A"},
		},
		{
			name: "year and ISBN-13 are kept",
			in:   bookInput{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("9780441172719")},
			want: Book{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("9780441172719")},
		},
		{
			name:       "year zero is below the minimum",
			in:         bookInput{Title: "T", Author: "A", Year: intPtr(0)},
			wantFields: []string{"year"},
		},
		{
			name:       "negative year",
			in:         bookInput{Title: "T", Author: "A", Year: intPtr(-700)},
			wantFields: []string{"year"},
		},
		{
			name:       "year beyond next year",
			in:         bookInput{Title: "T", Author: "A", Year: intPtr(fixedNow.Year() + 2)},
			wantFields: []string{"year"},
		},
		{
			name: "next year is accepted for forthcoming titles",
			in:   bookInput{Title: "T", Author: "A", Year: intPtr(fixedNow.Year() + 1)},
			want: Book{Title: "T", Author: "A", Year: intPtr(fixedNow.Year() + 1)},
		},
		{
			name: "ISBN-13 with hyphens is normalised",
			in:   bookInput{Title: "T", Author: "A", ISBN: strPtr("978-0-441-17271-9")},
			want: Book{Title: "T", Author: "A", ISBN: strPtr("9780441172719")},
		},
		{
			name: "ISBN-10 with hyphens is normalised",
			in:   bookInput{Title: "T", Author: "A", ISBN: strPtr("0-441-17271-7")},
			want: Book{Title: "T", Author: "A", ISBN: strPtr("0441172717")},
		},
		{
			name: "ISBN-10 ending in lower-case x is normalised to X",
			in:   bookInput{Title: "T", Author: "A", ISBN: strPtr("080442957x")},
			want: Book{Title: "T", Author: "A", ISBN: strPtr("080442957X")},
		},
		{
			name:       "ISBN with a bad check digit",
			in:         bookInput{Title: "T", Author: "A", ISBN: strPtr("9780441172718")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "ISBN-13 with a non-Bookland prefix",
			in:         bookInput{Title: "T", Author: "A", ISBN: strPtr("9770306406158")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "X only allowed as the last ISBN-10 character",
			in:         bookInput{Title: "T", Author: "A", ISBN: strPtr("08044X9572")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "ISBN of the wrong length",
			in:         bookInput{Title: "T", Author: "A", ISBN: strPtr("12345")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "ISBN with letters",
			in:         bookInput{Title: "T", Author: "A", ISBN: strPtr("abcdefghij")},
			wantFields: []string{"isbn"},
		},
		{
			name: "blank ISBN counts as absent",
			in:   bookInput{Title: "T", Author: "A", ISBN: strPtr("   ")},
			want: Book{Title: "T", Author: "A"},
		},
		{
			name:       "invalid year and ISBN are both reported",
			in:         bookInput{Title: "T", Author: "A", Year: intPtr(0), ISBN: strPtr("123")},
			wantFields: []string{"isbn", "year"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, errs := tt.in.toBook(fixedNow)

			gotFields := slices.Sorted(maps.Keys(errs))
			if !slices.Equal(gotFields, tt.wantFields) {
				t.Fatalf("invalid fields = %v, want %v (errors: %v)", gotFields, tt.wantFields, errs)
			}
			if tt.wantFields == nil && !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("book = %+v, want %+v", got, tt.want)
			}
		})
	}
}

func TestNormalizeISBN(t *testing.T) {
	// Check digits here were worked out by hand from the ISBN rules, not by running the code under test.
	valid := map[string]string{
		"9780306406157":     "9780306406157", // ISBN-13
		"978-0-306-40615-7": "9780306406157",
		"0306406152":        "0306406152", // ISBN-10
		"0 306 40615 2":     "0306406152",
		"080442957X":        "080442957X", // check digit X
		"0-8044-2957-x":     "080442957X",
	}
	for raw, want := range valid {
		got, ok := normalizeISBN(raw)
		if !ok || got != want {
			t.Errorf("normalizeISBN(%q) = %q, %v; want %q, true", raw, got, ok, want)
		}
	}

	invalid := []string{
		"",
		"978030640615",   // 12 digits
		"97803064061570", // 14 digits
		"9780306406158",  // check digit wrong
		"0306406153",     // check digit wrong
		"030640615X",     // check digit should be 2
		"9770306406158",  // valid checksum but not a Bookland prefix
		"978030640615A",  // non-digit in ISBN-13
	}
	for _, raw := range invalid {
		if got, ok := normalizeISBN(raw); ok {
			t.Errorf("normalizeISBN(%q) = %q, true; want invalid", raw, got)
		}
	}
}
