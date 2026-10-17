package main

import "testing"

func TestValidISBN(t *testing.T) {
	tests := []struct {
		isbn string
		want bool
	}{
		{"0306406152", true},        // ISBN-10
		{"0-8044-2957-X", true},     // ISBN-10 with X check digit and hyphens
		{"9780306406157", true},     // ISBN-13
		{"978-0-306-40615-7", true}, // ISBN-13 with hyphens
		{"9780306406158", false},    // ISBN-13 bad check digit
		{"0306406153", false},       // ISBN-10 bad check digit
		{"030640615X", false},       // X only allowed as ISBN-10 check digit
		{"123", false},              // wrong length
		{"978030640615A", false},    // non-digit
	}
	for _, tt := range tests {
		if got := validISBN(tt.isbn); got != tt.want {
			t.Errorf("validISBN(%q) = %v, want %v", tt.isbn, got, tt.want)
		}
	}
}

func TestBookInputValidate(t *testing.T) {
	tests := []struct {
		name   string
		in     BookInput
		fields []string // expected invalid fields; nil means valid
	}{
		{
			name:   "title and author only is valid",
			in:     BookInput{Title: "Dune", Author: "Frank Herbert"},
			fields: nil,
		},
		{
			name:   "missing title and author",
			in:     BookInput{},
			fields: []string{"title", "author"},
		},
		{
			name:   "whitespace-only title is rejected",
			in:     BookInput{Title: "   ", Author: "Frank Herbert"},
			fields: []string{"title"},
		},
		{
			name:   "negative year is rejected",
			in:     BookInput{Title: "Dune", Author: "Frank Herbert", Year: -5},
			fields: []string{"year"},
		},
		{
			name:   "year above maximum is rejected",
			in:     BookInput{Title: "Dune", Author: "Frank Herbert", Year: 10000},
			fields: []string{"year"},
		},
		{
			name:   "invalid isbn is rejected",
			in:     BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: "not-an-isbn"},
			fields: []string{"isbn"},
		},
		{
			name:   "valid year and isbn are accepted",
			in:     BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"},
			fields: nil,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			problems := tt.in.Validate()
			if len(problems) != len(tt.fields) {
				t.Fatalf("Validate() problems = %v, want fields %v", problems, tt.fields)
			}
			for _, f := range tt.fields {
				if _, ok := problems[f]; !ok {
					t.Errorf("Validate() missing problem for %q; got %v", f, problems)
				}
			}
		})
	}
}

func TestNormalizeTrimsWhitespace(t *testing.T) {
	in := BookInput{Title: "  Dune ", Author: " Frank Herbert\t", ISBN: " 0306406152 "}
	in.normalize()
	if in.Title != "Dune" || in.Author != "Frank Herbert" || in.ISBN != "0306406152" {
		t.Errorf("normalize() = %+v, want trimmed fields", in)
	}
}
