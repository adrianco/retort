package main

import (
	"testing"
	"time"
)

func TestISBNValidation(t *testing.T) {
	tests := []struct {
		isbn string
		want bool
	}{
		{"9780441172719", true},  // ISBN-13 (Dune)
		{"0441172717", true},     // ISBN-10 (Dune)
		{"080442957X", true},     // ISBN-10 with X check digit
		{"9780441172718", false}, // ISBN-13 bad check digit
		{"0441172716", false},    // ISBN-10 bad check digit
		{"12345", false},         // wrong length
		{"04411727AB", false},    // non-digit characters
	}
	for _, tt := range tests {
		if got := isValidISBN(tt.isbn); got != tt.want {
			t.Errorf("isValidISBN(%q) = %v, want %v", tt.isbn, got, tt.want)
		}
	}
}

func TestNormalizeStripsISBNFormatting(t *testing.T) {
	in := BookInput{Title: "  Dune ", Author: " Frank Herbert ", ISBN: "978-0 441-17271-9"}.normalize()
	if in.Title != "Dune" || in.Author != "Frank Herbert" {
		t.Errorf("whitespace not trimmed: %+v", in)
	}
	if in.ISBN != "9780441172719" {
		t.Errorf("ISBN = %q, want digits only", in.ISBN)
	}
}

func TestValidateYearBounds(t *testing.T) {
	now := time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC)
	base := BookInput{Title: "T", Author: "A"}

	ok := []int{0, 1, 1965, 2027}
	for _, y := range ok {
		in := base
		in.Year = y
		if errs := in.validate(now); len(errs) != 0 {
			t.Errorf("year %d: unexpected errors %v", y, errs)
		}
	}
	for _, y := range []int{-5, 2028} {
		in := base
		in.Year = y
		if _, bad := in.validate(now)["year"]; !bad {
			t.Errorf("year %d: expected validation error", y)
		}
	}
}
