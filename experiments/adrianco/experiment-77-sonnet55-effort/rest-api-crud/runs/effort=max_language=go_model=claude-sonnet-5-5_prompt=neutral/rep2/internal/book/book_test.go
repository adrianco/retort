package book_test

import (
	"errors"
	"maps"
	"strings"
	"testing"

	"bookapi/internal/book"
)

func TestValidate(t *testing.T) {
	tests := []struct {
		name string
		in   book.Input
		want book.ValidationError // nil means the input is valid
	}{
		{
			name: "title and author only",
			in:   book.Input{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name: "all fields",
			in:   book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441013593"},
		},
		{
			name: "missing title",
			in:   book.Input{Author: "Frank Herbert"},
			want: book.ValidationError{"title": "is required"},
		},
		{
			name: "missing author",
			in:   book.Input{Title: "Dune"},
			want: book.ValidationError{"author": "is required"},
		},
		{
			name: "missing both reports both",
			in:   book.Input{Year: 1965},
			want: book.ValidationError{"title": "is required", "author": "is required"},
		},
		{
			name: "whitespace-only title and author count as missing",
			in:   book.Input{Title: " \t\n", Author: "  "},
			want: book.ValidationError{"title": "is required", "author": "is required"},
		},
		{
			name: "title at the length limit",
			in:   book.Input{Title: strings.Repeat("x", book.MaxTextLength), Author: "A"},
		},
		{
			name: "title over the length limit",
			in:   book.Input{Title: strings.Repeat("x", book.MaxTextLength+1), Author: "A"},
			want: book.ValidationError{"title": "must be at most 255 characters"},
		},
		{
			name: "length is counted in characters, not bytes",
			in:   book.Input{Title: strings.Repeat("é", book.MaxTextLength), Author: strings.Repeat("村", book.MaxTextLength)},
		},
		{
			name: "author over the length limit",
			in:   book.Input{Title: "T", Author: strings.Repeat("x", book.MaxTextLength+1)},
			want: book.ValidationError{"author": "must be at most 255 characters"},
		},
		{
			name: "isbn at the length limit",
			in:   book.Input{Title: "T", Author: "A", ISBN: strings.Repeat("9", book.MaxISBNLength)},
		},
		{
			name: "isbn over the length limit",
			in:   book.Input{Title: "T", Author: "A", ISBN: strings.Repeat("9", book.MaxISBNLength+1)},
			want: book.ValidationError{"isbn": "must be at most 32 characters"},
		},
		{
			name: "isbn format is not checked",
			in:   book.Input{Title: "T", Author: "A", ISBN: "not-an-isbn"},
		},
		{
			name: "year zero means not provided",
			in:   book.Input{Title: "T", Author: "A", Year: 0},
		},
		{
			name: "year upper bound",
			in:   book.Input{Title: "T", Author: "A", Year: book.MaxYear},
		},
		{
			name: "year too large",
			in:   book.Input{Title: "T", Author: "A", Year: book.MaxYear + 1},
			want: book.ValidationError{"year": "must be between 0 and 9999"},
		},
		{
			name: "year negative",
			in:   book.Input{Title: "T", Author: "A", Year: -1},
			want: book.ValidationError{"year": "must be between 0 and 9999"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.in.Validate()
			if tt.want == nil {
				if err != nil {
					t.Fatalf("Validate() = %v, want nil", err)
				}
				return
			}

			var got book.ValidationError
			if !errors.As(err, &got) {
				t.Fatalf("Validate() = %v (%T), want a book.ValidationError", err, err)
			}
			if !maps.Equal(got, tt.want) {
				t.Errorf("Validate() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestNormalizeTrimsTextFields(t *testing.T) {
	in := book.Input{Title: "  Dune\n", Author: "\tFrank Herbert ", Year: 1965, ISBN: " 978 "}
	in.Normalize()

	want := book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978"}
	if in != want {
		t.Errorf("after Normalize = %+v, want %+v", in, want)
	}
}

func TestValidationErrorMessageIsSortedAndStable(t *testing.T) {
	err := book.ValidationError{"title": "is required", "author": "is required", "year": "must be between 0 and 9999"}

	want := "invalid book: author is required; title is required; year must be between 0 and 9999"
	for range 5 { // map iteration order is random; the message must not be
		if got := err.Error(); got != want {
			t.Fatalf("Error() = %q, want %q", got, want)
		}
	}
}
