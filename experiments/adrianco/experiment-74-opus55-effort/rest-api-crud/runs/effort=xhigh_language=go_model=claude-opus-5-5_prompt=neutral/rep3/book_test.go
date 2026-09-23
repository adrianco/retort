package main

import (
	"maps"
	"slices"
	"strings"
	"testing"
	"time"
)

func TestNormalizeISBN(t *testing.T) {
	tests := []struct {
		in    string
		want  string
		valid bool
	}{
		{"0-306-40615-2", "0306406152", true},
		{"080442957X", "080442957X", true},
		{"080442957x", "080442957X", true},
		{"978-0-306-40615-7", "9780306406157", true},
		{"978 3 16 148410 0", "9783161484100", true},
		{" 9780134685991 ", "9780134685991", true},
		{"0306406153", "", false},        // bad ISBN-10 checksum
		{"978-0-306-40615-8", "", false}, // bad ISBN-13 checksum
		{"X306406152", "", false},        // X only allowed as ISBN-10 check digit
		{"978030640615X", "", false},     // X never allowed in ISBN-13
		{"abcdefghij", "", false},
		{"12345", "", false},
		{"97803064061570", "", false},
		{"", "", false},
	}
	for _, tt := range tests {
		got, ok := normalizeISBN(tt.in)
		if ok != tt.valid {
			t.Errorf("normalizeISBN(%q) valid = %v, want %v", tt.in, ok, tt.valid)
			continue
		}
		if ok && got != tt.want {
			t.Errorf("normalizeISBN(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}

func TestBookInputNormalize(t *testing.T) {
	now := time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC)
	ptr := func(s string) *string { return &s }
	year := func(y int) *int { return &y }

	t.Run("trims and canonicalises", func(t *testing.T) {
		got, err := BookInput{
			Title:  "  Dune ",
			Author: "\tFrank Herbert\n",
			Year:   year(1965),
			ISBN:   ptr("978-0-306-40615-7"),
		}.Normalize(now)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got.Title != "Dune" || got.Author != "Frank Herbert" {
			t.Errorf("title/author not trimmed: %q / %q", got.Title, got.Author)
		}
		if got.Year == nil || *got.Year != 1965 {
			t.Errorf("year = %v, want 1965", got.Year)
		}
		if got.ISBN == nil || *got.ISBN != "9780306406157" {
			t.Errorf("isbn = %v, want 9780306406157", got.ISBN)
		}
	})

	t.Run("blank isbn means absent", func(t *testing.T) {
		for _, isbn := range []*string{nil, ptr(""), ptr("   ")} {
			got, err := BookInput{Title: "T", Author: "A", ISBN: isbn}.Normalize(now)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.ISBN != nil {
				t.Errorf("isbn = %q, want nil", *got.ISBN)
			}
		}
	})

	t.Run("accepts next year for forthcoming books", func(t *testing.T) {
		if _, err := (BookInput{Title: "T", Author: "A", Year: year(2027)}).Normalize(now); err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
	})

	invalid := []struct {
		name   string
		in     BookInput
		fields []string
	}{
		{"missing title", BookInput{Author: "A"}, []string{"title"}},
		{"missing author", BookInput{Title: "T"}, []string{"author"}},
		{"whitespace only", BookInput{Title: "  ", Author: "\t"}, []string{"author", "title"}},
		{"title too long", BookInput{Title: strings.Repeat("é", maxTitleLen+1), Author: "A"}, []string{"title"}},
		{"author too long", BookInput{Title: "T", Author: strings.Repeat("a", maxAuthorLen+1)}, []string{"author"}},
		{"year zero", BookInput{Title: "T", Author: "A", Year: year(0)}, []string{"year"}},
		{"year negative", BookInput{Title: "T", Author: "A", Year: year(-400)}, []string{"year"}},
		{"year too far ahead", BookInput{Title: "T", Author: "A", Year: year(2028)}, []string{"year"}},
		{"bad isbn", BookInput{Title: "T", Author: "A", ISBN: ptr("123-456")}, []string{"isbn"}},
		{"everything wrong", BookInput{Year: year(0), ISBN: ptr("nope")}, []string{"author", "isbn", "title", "year"}},
	}
	for _, tt := range invalid {
		t.Run(tt.name, func(t *testing.T) {
			_, err := tt.in.Normalize(now)
			verr, ok := err.(ValidationError)
			if !ok {
				t.Fatalf("error = %v (%T), want ValidationError", err, err)
			}
			if got := slices.Sorted(maps.Keys(verr)); !slices.Equal(got, tt.fields) {
				t.Errorf("invalid fields = %v, want %v", got, tt.fields)
			}
		})
	}

	// Titles are measured in characters, not bytes.
	if _, err := (BookInput{Title: strings.Repeat("é", maxTitleLen), Author: "A"}).Normalize(now); err != nil {
		t.Errorf("title of exactly %d multi-byte characters rejected: %v", maxTitleLen, err)
	}
}
