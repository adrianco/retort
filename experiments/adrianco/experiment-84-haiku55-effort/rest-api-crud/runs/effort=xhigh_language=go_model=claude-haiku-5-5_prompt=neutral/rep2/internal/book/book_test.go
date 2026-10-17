package book

import (
	"reflect"
	"strings"
	"testing"
	"time"
)

func intPtr(v int) *int       { return &v }
func strPtr(v string) *string { return &v }

func TestNormalize(t *testing.T) {
	in := Input{
		Title:  "  The Go Programming Language  ",
		Author: "\tAlan A. A. Donovan ",
		Year:   intPtr(2015),
		ISBN:   strPtr(" 978-0-13-419044-0 "),
	}

	got := in.Normalize()

	want := Input{
		Title:  "The Go Programming Language",
		Author: "Alan A. A. Donovan",
		Year:   intPtr(2015),
		ISBN:   strPtr("9780134190440"),
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("Normalize() = %+v, want %+v", got, want)
	}
}

func TestNormalizeBlankISBNBecomesNil(t *testing.T) {
	for _, isbn := range []string{"", "   ", "--"} {
		got := Input{Title: "t", Author: "a", ISBN: strPtr(isbn)}.Normalize()
		if got.ISBN != nil {
			t.Errorf("ISBN %q: Normalize() ISBN = %q, want nil", isbn, *got.ISBN)
		}
	}
}

func TestNormalizeUppercasesISBN10CheckCharacter(t *testing.T) {
	got := Input{Title: "t", Author: "a", ISBN: strPtr("080442957x")}.Normalize()
	if got.ISBN == nil || *got.ISBN != "080442957X" {
		t.Errorf("Normalize() ISBN = %v, want 080442957X", got.ISBN)
	}
}

func TestValidate(t *testing.T) {
	nextYear := time.Now().Year() + 1
	tooLongTitle := strings.Repeat("a", maxTitleLen+1)
	tooLongAuthor := strings.Repeat("b", maxAuthorLen+1)

	tests := []struct {
		name   string
		input  Input
		fields []string // expected error keys; empty means valid
	}{
		{
			name:  "minimal valid book",
			input: Input{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name:  "all fields valid",
			input: Input{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("9780441013593")},
		},
		{
			name:   "missing title and author",
			input:  Input{},
			fields: []string{"title", "author"},
		},
		{
			name:   "missing author",
			input:  Input{Title: "Dune"},
			fields: []string{"author"},
		},
		{
			name:   "missing title",
			input:  Input{Author: "Frank Herbert"},
			fields: []string{"title"},
		},
		{
			name:   "title too long",
			input:  Input{Title: tooLongTitle, Author: "a"},
			fields: []string{"title"},
		},
		{
			name:   "author too long",
			input:  Input{Title: "t", Author: tooLongAuthor},
			fields: []string{"author"},
		},
		{
			name:  "title at maximum length is accepted",
			input: Input{Title: strings.Repeat("é", maxTitleLen), Author: "a"},
		},
		{
			name:  "year at lower bound",
			input: Input{Title: "t", Author: "a", Year: intPtr(minYear)},
		},
		{
			name:  "year at upper bound is next year",
			input: Input{Title: "t", Author: "a", Year: intPtr(nextYear)},
		},
		{
			name:   "year below lower bound",
			input:  Input{Title: "t", Author: "a", Year: intPtr(minYear - 1)},
			fields: []string{"year"},
		},
		{
			name:   "year beyond next year",
			input:  Input{Title: "t", Author: "a", Year: intPtr(nextYear + 1)},
			fields: []string{"year"},
		},
		{
			name:  "valid ISBN-10",
			input: Input{Title: "t", Author: "a", ISBN: strPtr("0306406152")},
		},
		{
			name:  "valid ISBN-10 with X check digit",
			input: Input{Title: "t", Author: "a", ISBN: strPtr("080442957X")},
		},
		{
			name:   "ISBN-10 with bad check digit",
			input:  Input{Title: "t", Author: "a", ISBN: strPtr("0306406153")},
			fields: []string{"isbn"},
		},
		{
			name:   "ISBN-13 with bad check digit",
			input:  Input{Title: "t", Author: "a", ISBN: strPtr("9780306406158")},
			fields: []string{"isbn"},
		},
		{
			name:   "ISBN with wrong length",
			input:  Input{Title: "t", Author: "a", ISBN: strPtr("12345")},
			fields: []string{"isbn"},
		},
		{
			name:   "ISBN with letters in the body",
			input:  Input{Title: "t", Author: "a", ISBN: strPtr("03064X6152")},
			fields: []string{"isbn"},
		},
		{
			name:   "ISBN-13 with an X",
			input:  Input{Title: "t", Author: "a", ISBN: strPtr("978030640615X")},
			fields: []string{"isbn"},
		},
		{
			name:   "multiple problems are all reported",
			input:  Input{Year: intPtr(1), ISBN: strPtr("bad")},
			fields: []string{"title", "author", "isbn"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			errs := tt.input.Normalize().Validate()

			if len(tt.fields) == 0 {
				if errs != nil {
					t.Fatalf("Validate() = %v, want no errors", errs)
				}
				return
			}
			if len(errs) != len(tt.fields) {
				t.Fatalf("Validate() = %v, want errors for %v", errs, tt.fields)
			}
			for _, f := range tt.fields {
				if _, ok := errs[f]; !ok {
					t.Errorf("Validate() = %v, missing error for %q", errs, f)
				}
			}
		})
	}
}

func TestValidISBN(t *testing.T) {
	// Well-known examples from the ISBN specifications.
	valid := []string{"0306406152", "080442957X", "9780306406157", "9780134190440"}
	invalid := []string{
		"",
		"030640615",     // 9 digits
		"03064061522",   // 11 digits
		"030640615X",    // X only allowed as the last char of ISBN-10
		"0306406151",    // ISBN-10 checksum off by one
		"9780306406156", // ISBN-13 checksum off by one
		"978030640615A",
	}

	for _, s := range valid {
		if !validISBN(s) {
			t.Errorf("validISBN(%q) = false, want true", s)
		}
	}
	for _, s := range invalid {
		if validISBN(s) {
			t.Errorf("validISBN(%q) = true, want false", s)
		}
	}
}
