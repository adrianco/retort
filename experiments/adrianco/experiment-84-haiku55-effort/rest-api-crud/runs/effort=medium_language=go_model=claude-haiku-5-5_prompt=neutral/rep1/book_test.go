package main

import (
	"testing"
	"time"
)

func TestValidateRequiresTitleAndAuthor(t *testing.T) {
	problems := BookInput{Year: 2000}.normalize().Validate()
	if problems["title"] == "" {
		t.Errorf("expected title to be required, got %v", problems)
	}
	if problems["author"] == "" {
		t.Errorf("expected author to be required, got %v", problems)
	}
}

func TestValidateRejectsWhitespaceOnlyTitle(t *testing.T) {
	in := BookInput{Title: "   ", Author: "Ursula K. Le Guin", Year: 1969}.normalize()
	if _, ok := in.Validate()["title"]; !ok {
		t.Error("expected whitespace-only title to be rejected")
	}
}

func TestValidateYearRange(t *testing.T) {
	maxYear := time.Now().Year() + 1
	cases := []struct {
		year int
		ok   bool
	}{
		{0, true},
		{1969, true},
		{maxYear, true},
		{-1, false},
		{maxYear + 1, false},
	}
	for _, c := range cases {
		in := BookInput{Title: "T", Author: "A", Year: c.year}
		_, bad := in.Validate()["year"]
		if bad == c.ok {
			t.Errorf("year %d: valid=%v, want %v", c.year, !bad, c.ok)
		}
	}
}

func TestValidISBN(t *testing.T) {
	cases := []struct {
		isbn string
		ok   bool
	}{
		{"0306406152", true},     // ISBN-10
		{"030640615X", false},    // wrong check digit
		{"0-306-40615-2", true},  // hyphens are stripped during normalisation
		{"9780306406157", true},  // ISBN-13
		{"9780306406158", false}, // wrong check digit
		{"978030640615", false},  // wrong length
		{"97803064061ab", false}, // non-digit
		{"0-8044-2957-X", true},  // ISBN-10 with X check digit
	}
	for _, c := range cases {
		if got := validISBN(normalizeISBN(c.isbn)); got != c.ok {
			t.Errorf("validISBN(%q) = %v, want %v", c.isbn, got, c.ok)
		}
	}
}

func TestNormalizeTrimsAndCanonicalisesISBN(t *testing.T) {
	in := BookInput{Title: "  Dune  ", Author: " Frank Herbert ", Year: 1965, ISBN: "0-8044-2957-x"}.normalize()
	if in.Title != "Dune" || in.Author != "Frank Herbert" {
		t.Errorf("whitespace not trimmed: %+v", in)
	}
	if in.ISBN != "080442957X" {
		t.Errorf("ISBN not canonicalised: %q", in.ISBN)
	}
}

func TestValidateAcceptsEmptyISBN(t *testing.T) {
	in := BookInput{Title: "T", Author: "A", Year: 2001}.normalize()
	if len(in.Validate()) != 0 {
		t.Errorf("expected no problems for book without ISBN, got %v", in.Validate())
	}
}
