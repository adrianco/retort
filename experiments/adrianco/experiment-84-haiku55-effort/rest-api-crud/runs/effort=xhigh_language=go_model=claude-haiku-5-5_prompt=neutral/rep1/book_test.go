package main

import (
	"fmt"
	"strings"
	"testing"
	"time"
)

func TestNormalizeRequiresTitleAndAuthor(t *testing.T) {
	tests := []struct {
		name   string
		input  BookInput
		fields []string
	}{
		{"valid minimal", BookInput{Title: "Dune", Author: "Frank Herbert"}, nil},
		{"missing title", BookInput{Author: "Frank Herbert"}, []string{"title"}},
		{"blank title", BookInput{Title: "   ", Author: "Frank Herbert"}, []string{"title"}},
		{"missing author", BookInput{Title: "Dune"}, []string{"author"}},
		{"both missing", BookInput{}, []string{"title", "author"}},
		{"title too long", BookInput{Title: strings.Repeat("t", maxTitleLen+1), Author: "A"}, []string{"title"}},
		{"title at limit", BookInput{Title: strings.Repeat("t", maxTitleLen), Author: "A"}, nil},
		{"author too long", BookInput{Title: "T", Author: strings.Repeat("a", maxAuthorLen+1)}, []string{"author"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, problems := tt.input.Normalize()
			if len(problems) != len(tt.fields) {
				t.Fatalf("problems = %v, want fields %v", problems, tt.fields)
			}
			for _, f := range tt.fields {
				if _, ok := problems[f]; !ok {
					t.Errorf("problems = %v, missing field %q", problems, f)
				}
			}
		})
	}
}

func TestNormalizeTrimsWhitespace(t *testing.T) {
	in, problems := BookInput{Title: "  Dune \t", Author: "\nFrank Herbert  ", ISBN: " 978-0-306-40615-7 "}.Normalize()
	if len(problems) > 0 {
		t.Fatalf("unexpected problems: %v", problems)
	}
	if in.Title != "Dune" {
		t.Errorf("Title = %q, want %q", in.Title, "Dune")
	}
	if in.Author != "Frank Herbert" {
		t.Errorf("Author = %q, want %q", in.Author, "Frank Herbert")
	}
	if in.ISBN != "9780306406157" {
		t.Errorf("ISBN = %q, want hyphens and spaces removed", in.ISBN)
	}
}

func TestNormalizeYear(t *testing.T) {
	nextYear := time.Now().Year() + 1
	tests := []struct {
		name    string
		year    int
		wantErr bool
	}{
		{"unknown (zero)", 0, false},
		{"first year", 1, false},
		{"classic", 1965, false},
		{"next year (forthcoming)", nextYear, false},
		{"negative", -1, true},
		{"beyond next year", nextYear + 1, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, problems := BookInput{Title: "T", Author: "A", Year: tt.year}.Normalize()
			if _, bad := problems["year"]; bad != tt.wantErr {
				t.Errorf("year %d: problems = %v, wantErr = %v", tt.year, problems, tt.wantErr)
			}
		})
	}
}

func TestNormalizeISBN(t *testing.T) {
	tests := []struct {
		isbn    string
		wantErr bool
	}{
		{"", false},                  // optional
		{"0306406152", false},        // ISBN-10
		{"0-306-40615-2", false},     // ISBN-10 with hyphens
		{"080442957X", false},        // ISBN-10 with X check digit
		{"080442957x", false},        // lower-case x is accepted
		{"9780306406157", false},     // ISBN-13
		{"978-0-306-40615-7", false}, // ISBN-13 with hyphens
		{"0306406153", true},         // ISBN-10 bad check digit
		{"9780306406158", true},      // ISBN-13 bad check digit
		{"978030640615X", true},      // X only allowed in ISBN-10
		{"080442X957", true},         // X in the middle
		{"12345", true},              // wrong length
		{"abcdefghij", true},         // not digits
		{"ISBN 0306406152", true},    // prefix not allowed
	}
	for _, tt := range tests {
		t.Run(fmt.Sprintf("%q", tt.isbn), func(t *testing.T) {
			_, problems := BookInput{Title: "T", Author: "A", ISBN: tt.isbn}.Normalize()
			if _, bad := problems["isbn"]; bad != tt.wantErr {
				t.Errorf("isbn %q: problems = %v, wantErr = %v", tt.isbn, problems, tt.wantErr)
			}
		})
	}
}
