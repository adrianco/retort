package book_test

import (
	"encoding/json"
	"errors"
	"reflect"
	"strings"
	"testing"

	"bookapi/internal/book"
)

func ptr[T any](v T) *T { return &v }

func TestNormalized(t *testing.T) {
	orig := book.Input{Title: "  Dune ", Author: "\nFrank Herbert\t", Year: ptr(1965), ISBN: ptr("  978-0  ")}

	got := orig.Normalized()
	if got.Title != "Dune" || got.Author != "Frank Herbert" {
		t.Errorf("title/author = %q/%q, want them trimmed", got.Title, got.Author)
	}
	if got.ISBN == nil || *got.ISBN != "978-0" {
		t.Errorf("isbn = %v, want it trimmed to 978-0", got.ISBN)
	}
	if got.Year == nil || *got.Year != 1965 {
		t.Errorf("year = %v, want 1965", got.Year)
	}

	// The receiver must not change: callers may still hold the original.
	if orig.Title != "  Dune " || *orig.ISBN != "  978-0  " {
		t.Errorf("Normalized modified its receiver: %+v", orig)
	}
}

func TestNormalizedTreatsABlankISBNAsAbsent(t *testing.T) {
	for _, isbn := range []*string{nil, ptr(""), ptr(" \t\n ")} {
		in := book.Input{Title: "T", Author: "A", ISBN: isbn}
		if got := in.Normalized(); got.ISBN != nil {
			t.Errorf("isbn %v normalized to %q, want nil", isbn, *got.ISBN)
		}
	}
}

func TestValidate(t *testing.T) {
	text := func(n int) string { return strings.Repeat("x", n) }

	tests := []struct {
		name string
		in   book.Input
		want string // the expected error text; empty means the input is valid
	}{
		{"only the required fields", book.Input{Title: "T", Author: "A"}, ""},
		{"every field", book.Input{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("9780441172719")}, ""},

		{"missing title", book.Input{Author: "A"}, "title is required"},
		{"whitespace-only title", book.Input{Title: " \t\n", Author: "A"}, "title is required"},
		{"missing author", book.Input{Title: "T"}, "author is required"},
		{"whitespace-only author", book.Input{Title: "T", Author: "   "}, "author is required"},
		{"missing both", book.Input{}, "title is required; author is required"},

		{"year at the lower bound", book.Input{Title: "T", Author: "A", Year: ptr(0)}, ""},
		{"year at the upper bound", book.Input{Title: "T", Author: "A", Year: ptr(9999)}, ""},
		{"year below the range", book.Input{Title: "T", Author: "A", Year: ptr(-1)}, "year must be between 0 and 9999"},
		{"year above the range", book.Input{Title: "T", Author: "A", Year: ptr(10000)}, "year must be between 0 and 9999"},

		{"title at the length limit", book.Input{Title: text(500), Author: "A"}, ""},
		{"title over the length limit", book.Input{Title: text(501), Author: "A"}, "title must be at most 500 characters"},
		{"author at the length limit", book.Input{Title: "T", Author: text(500)}, ""},
		{"author over the length limit", book.Input{Title: "T", Author: text(501)}, "author must be at most 500 characters"},
		{"length counts characters, not bytes", book.Input{Title: strings.Repeat("é", 500), Author: "A"}, ""},
		{"length is measured after trimming", book.Input{Title: "  " + text(500) + "  ", Author: "A"}, ""},

		{"NUL inside the title", book.Input{Title: "a\x00b", Author: "A"}, "title must not contain control characters"},
		{"title starting with NUL", book.Input{Title: "\x00abc", Author: "A"}, "title must not contain control characters"},
		{"title made only of NULs", book.Input{Title: "\x00\x00", Author: "A"}, "title must not contain control characters"},
		{"newline inside the author", book.Input{Title: "T", Author: "Frank\nHerbert"}, "author must not contain control characters"},
		{"terminal escape in the title", book.Input{Title: "\x1b[31mred", Author: "A"}, "title must not contain control characters"},
		{"DEL in the title", book.Input{Title: "a\x7fb", Author: "A"}, "title must not contain control characters"},
		{"C1 control in the title", book.Input{Title: "a" + string(rune(0x85)) + "b", Author: "A"}, "title must not contain control characters"},
		{"NUL in the isbn", book.Input{Title: "T", Author: "A", ISBN: ptr("1\x00")}, "isbn must not contain control characters"},
		{"whitespace at the edges is trimmed, not rejected", book.Input{Title: "\tDune\n", Author: " Frank Herbert\r\n"}, ""},
		{"zero-width joiner, as used in emoji sequences, is fine", book.Input{Title: "a" + string(rune(0x200d)) + "b", Author: "A"}, ""},

		{"isbn at the length limit", book.Input{Title: "T", Author: "A", ISBN: ptr(text(32))}, ""},
		{"isbn over the length limit", book.Input{Title: "T", Author: "A", ISBN: ptr(text(33))}, "isbn must be at most 32 characters"},
		{"isbn format is not policed", book.Input{Title: "T", Author: "A", ISBN: ptr("not-a-real-isbn")}, ""},
		{"blank isbn is fine", book.Input{Title: "T", Author: "A", ISBN: ptr("   ")}, ""},

		{"every problem is reported in field order",
			book.Input{Year: ptr(-5), ISBN: ptr(text(40))},
			"title is required; author is required; year must be between 0 and 9999; isbn must be at most 32 characters"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.in.Validate()
			switch {
			case tt.want == "" && err != nil:
				t.Errorf("Validate() = %q, want it to be valid", err)
			case tt.want != "" && err == nil:
				t.Errorf("Validate() = nil, want %q", tt.want)
			case tt.want != "" && err.Error() != tt.want:
				t.Errorf("Validate() = %q, want %q", err, tt.want)
			}
		})
	}
}

func TestValidationErrorExposesEachField(t *testing.T) {
	err := book.Input{Year: ptr(-1)}.Validate()

	var ve book.ValidationError
	if !errors.As(err, &ve) {
		t.Fatalf("Validate() = %T, want a book.ValidationError", err)
	}
	want := book.ValidationError{
		{Field: "title", Message: "is required"},
		{Field: "author", Message: "is required"},
		{Field: "year", Message: "must be between 0 and 9999"},
	}
	if !reflect.DeepEqual(ve, want) {
		t.Errorf("fields = %+v, want %+v", ve, want)
	}
}

// The JSON field names are part of the API contract.
func TestBookJSON(t *testing.T) {
	full, err := json.Marshal(book.Book{ID: 7, Input: book.Input{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("978")}})
	if err != nil {
		t.Fatal(err)
	}
	if want := `{"id":7,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978"}`; string(full) != want {
		t.Errorf("full book = %s, want %s", full, want)
	}

	sparse, err := json.Marshal(book.Book{ID: 8, Input: book.Input{Title: "Emma", Author: "Jane Austen"}})
	if err != nil {
		t.Fatal(err)
	}
	if want := `{"id":8,"title":"Emma","author":"Jane Austen","year":null,"isbn":null}`; string(sparse) != want {
		t.Errorf("sparse book = %s, want %s", sparse, want)
	}

	var in book.Input
	if err := json.Unmarshal([]byte(`{"id":99,"title":"T","author":"A","year":2001,"extra":true}`), &in); err != nil {
		t.Fatalf("unknown fields must be ignored: %v", err)
	}
	if in.Title != "T" || in.Author != "A" || in.Year == nil || *in.Year != 2001 {
		t.Errorf("decoded input = %+v", in)
	}
}
