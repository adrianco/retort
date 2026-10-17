package main

import (
	"strings"
	"testing"
	"time"
)

var testNow = time.Date(2026, time.October, 17, 0, 0, 0, 0, time.UTC)

func ptr[T any](v T) *T { return &v }

func TestValidateBook(t *testing.T) {
	tests := []struct {
		name       string
		in         BookInput
		wantFields []string // nil means the input is valid
	}{
		{
			name: "title and author only",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name: "all fields",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("0306406152")},
		},
		{
			name:       "missing title",
			in:         BookInput{Author: "Frank Herbert"},
			wantFields: []string{"title"},
		},
		{
			name:       "whitespace-only author",
			in:         BookInput{Title: "Dune", Author: "   "},
			wantFields: []string{"author"},
		},
		{
			name:       "title too long",
			in:         BookInput{Title: strings.Repeat("a", maxTextLength+1), Author: "X"},
			wantFields: []string{"title"},
		},
		{
			name:       "year zero",
			in:         BookInput{Title: "T", Author: "A", Year: ptr(0)},
			wantFields: []string{"year"},
		},
		{
			name:       "year in the far future",
			in:         BookInput{Title: "T", Author: "A", Year: ptr(3000)},
			wantFields: []string{"year"},
		},
		{
			name:       "bad isbn checksum",
			in:         BookInput{Title: "T", Author: "A", ISBN: ptr("9780306406158")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "isbn with wrong length",
			in:         BookInput{Title: "T", Author: "A", ISBN: ptr("12345")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "several problems reported together",
			in:         BookInput{Author: "", Year: ptr(0), ISBN: ptr("nope")},
			wantFields: []string{"title", "author", "year", "isbn"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, errs := validateBook(tt.in, testNow)
			if tt.wantFields == nil {
				if errs != nil {
					t.Fatalf("expected valid input, got errors: %v", errs)
				}
				return
			}
			for _, f := range tt.wantFields {
				if _, ok := errs[f]; !ok {
					t.Errorf("expected error on %q, got errors: %v", f, errs)
				}
			}
			if len(errs) != len(tt.wantFields) {
				t.Errorf("expected exactly %d field errors, got %v", len(tt.wantFields), errs)
			}
		})
	}
}

func TestValidateBookTrimsAndNormalizes(t *testing.T) {
	book, errs := validateBook(BookInput{
		Title:  "  The Left Hand of Darkness ",
		Author: " Ursula K. Le Guin\t",
		ISBN:   ptr(" 0-8044-2957-x "),
	}, testNow)
	if errs != nil {
		t.Fatalf("unexpected errors: %v", errs)
	}
	if book.Title != "The Left Hand of Darkness" || book.Author != "Ursula K. Le Guin" {
		t.Errorf("text not trimmed: %+v", book)
	}
	if book.ISBN == nil || *book.ISBN != "080442957X" {
		t.Errorf("ISBN not normalized to 080442957X: %v", book.ISBN)
	}
}

func TestValidateBookBlankISBNIsUnset(t *testing.T) {
	book, errs := validateBook(BookInput{Title: "T", Author: "A", ISBN: ptr("  - ")}, testNow)
	if errs != nil {
		t.Fatalf("unexpected errors: %v", errs)
	}
	if book.ISBN != nil {
		t.Errorf("blank ISBN should be unset, got %q", *book.ISBN)
	}
}

func TestValidateBookYearUpperBoundAllowsNextYear(t *testing.T) {
	if _, errs := validateBook(BookInput{Title: "T", Author: "A", Year: ptr(2027)}, testNow); errs != nil {
		t.Errorf("year 2027 should be accepted in 2026: %v", errs)
	}
	if _, errs := validateBook(BookInput{Title: "T", Author: "A", Year: ptr(2028)}, testNow); errs == nil {
		t.Errorf("year 2028 should be rejected in 2026")
	}
}

func TestValidISBN(t *testing.T) {
	tests := []struct {
		isbn string
		want bool
	}{
		{"0306406152", true},     // ISBN-10
		{"080442957X", true},     // ISBN-10 with X check digit
		{"9780306406157", true},  // ISBN-13
		{"9790306406156", true},  // ISBN-13, 979 prefix
		{"9780306406158", false}, // ISBN-13 bad check digit
		{"0306406153", false},    // ISBN-10 bad check digit
		{"X306406152", false},    // X only allowed as the final ISBN-10 character
		{"1234567890123", false}, // ISBN-13 without 978/979 prefix
		{"978030640615A", false}, // non-digit
		{"123456789", false},     // wrong length
		{"", false},              // empty
	}
	for _, tt := range tests {
		if got := validISBN(tt.isbn); got != tt.want {
			t.Errorf("validISBN(%q) = %v, want %v", tt.isbn, got, tt.want)
		}
	}
}
