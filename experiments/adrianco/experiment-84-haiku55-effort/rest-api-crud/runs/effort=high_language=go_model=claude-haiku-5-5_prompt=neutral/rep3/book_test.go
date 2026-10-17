package bookapi

import (
	"testing"
	"time"
)

func TestBookInputValidate(t *testing.T) {
	nextYear := time.Now().Year() + 1

	tests := []struct {
		name       string
		in         BookInput
		wantFields []string // empty means valid
	}{
		{
			name: "valid full book",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"},
		},
		{
			name: "valid with optional fields omitted",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name:       "missing title and author",
			in:         BookInput{Year: 1965},
			wantFields: []string{"title", "author"},
		},
		{
			name:       "whitespace-only title is missing",
			in:         BookInput{Title: "   ", Author: "Frank Herbert"}.Clean(),
			wantFields: []string{"title"},
		},
		{
			name:       "negative year",
			in:         BookInput{Title: "X", Author: "Y", Year: -5},
			wantFields: []string{"year"},
		},
		{
			name:       "year too far in the future",
			in:         BookInput{Title: "X", Author: "Y", Year: nextYear + 1},
			wantFields: []string{"year"},
		},
		{
			name: "year at the next-year boundary is accepted",
			in:   BookInput{Title: "X", Author: "Y", Year: nextYear},
		},
		{
			name:       "invalid isbn",
			in:         BookInput{Title: "X", Author: "Y", ISBN: "12345"}.Clean(),
			wantFields: []string{"isbn"},
		},
		{
			name: "valid isbn-10 with hyphens is accepted after cleaning",
			in:   BookInput{Title: "X", Author: "Y", ISBN: "0-306-40615-2"}.Clean(),
		},
		{
			name: "isbn-10 ending in X is accepted",
			in:   BookInput{Title: "X", Author: "Y", ISBN: "155404295x"}.Clean(),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.in.Validate()
			if len(tt.wantFields) == 0 {
				if err != nil {
					t.Fatalf("Validate() = %v, want nil", err)
				}
				return
			}
			verr, ok := err.(ValidationError)
			if !ok {
				t.Fatalf("Validate() = %v (%T), want ValidationError", err, err)
			}
			for _, f := range tt.wantFields {
				if _, ok := verr[f]; !ok {
					t.Errorf("ValidationError %v missing field %q", verr, f)
				}
			}
			if len(verr) != len(tt.wantFields) {
				t.Errorf("ValidationError fields = %v, want exactly %v", verr, tt.wantFields)
			}
		})
	}
}

func TestValidISBN(t *testing.T) {
	tests := map[string]bool{
		"0306406152":      true,  // ISBN-10
		"080442957X":      true,  // ISBN-10 with X check digit
		"9780306406157":   true,  // ISBN-13
		"9780306406158":   false, // ISBN-13 bad check digit
		"0306406153":      false, // ISBN-10 bad check digit
		"X306406152":      false, // X only allowed as ISBN-10 check digit
		"97803064061X7":   false, // non-digit in ISBN-13
		"":                false,
		"123456789012345": false, // wrong length
	}
	for isbn, want := range tests {
		if got := validISBN(isbn); got != want {
			t.Errorf("validISBN(%q) = %v, want %v", isbn, got, want)
		}
	}
}

func TestCleanISBN(t *testing.T) {
	if got := cleanISBN(" 978-0-306-40615-7 "); got != "9780306406157" {
		t.Errorf("cleanISBN = %q, want %q", got, "9780306406157")
	}
	if got := cleanISBN("155404295x"); got != "155404295X" {
		t.Errorf("cleanISBN = %q, want %q", got, "155404295X")
	}
}
