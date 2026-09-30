package book_test

import (
	"errors"
	"fmt"
	"slices"
	"strings"
	"testing"

	"bookapi/internal/book"
)

// Invisible characters are built from their code points so that they can be
// seen in this source file.
var (
	zeroWidthSpace     = string(rune(0x200B))
	wordJoiner         = string(rune(0x2060))
	byteOrderMark      = string(rune(0xFEFF)) // also the zero-width no-break space
	zeroWidthJoiner    = string(rune(0x200D))
	zeroWidthNonJoiner = string(rune(0x200C))
	replacementChar    = string(rune(0xFFFD))
)

func fieldErr(field, message string) book.FieldError {
	return book.FieldError{Field: field, Message: message}
}

func TestValidate(t *testing.T) {
	const required = "is required"
	control := "must not contain control characters"
	tooLong := func(limit int) string { return fmt.Sprintf("must be at most %d characters", limit) }
	yearRange := fmt.Sprintf("must be between %d and %d", book.MinYear, book.MaxYear)

	tests := []struct {
		name string
		in   book.Input
		want []book.FieldError // nil means the input is valid
	}{
		{
			name: "complete book",
			in:   book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719"},
		},
		{
			name: "only the required fields",
			in:   book.Input{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name: "missing title",
			in:   book.Input{Author: "Frank Herbert"},
			want: []book.FieldError{fieldErr("title", required)},
		},
		{
			name: "missing author",
			in:   book.Input{Title: "Dune"},
			want: []book.FieldError{fieldErr("author", required)},
		},
		{
			name: "blank title and author",
			in:   book.Input{Title: " \t ", Author: "\n"},
			want: []book.FieldError{fieldErr("title", required), fieldErr("author", required)},
		},
		{
			name: "zero-width characters only",
			in:   book.Input{Title: zeroWidthSpace + wordJoiner + byteOrderMark, Author: zeroWidthJoiner + " " + zeroWidthNonJoiner},
			want: []book.FieldError{fieldErr("title", required), fieldErr("author", required)},
		},
		{
			name: "replacement characters only, which is what invalid UTF-8 decodes to",
			in:   book.Input{Title: replacementChar + replacementChar, Author: "A"},
			want: []book.FieldError{fieldErr("title", required)},
		},
		{
			name: "zero-width joiners inside real text are legitimate",
			in: book.Input{
				Title:  "می" + zeroWidthNonJoiner + "خواهم",
				Author: "👨" + zeroWidthJoiner + "👩" + zeroWidthJoiner + "👧",
			},
		},
		{
			name: "title at the length limit",
			in:   book.Input{Title: strings.Repeat("x", book.MaxTitleLength), Author: "A"},
		},
		{
			name: "title over the length limit",
			in:   book.Input{Title: strings.Repeat("x", book.MaxTitleLength+1), Author: "A"},
			want: []book.FieldError{fieldErr("title", tooLong(book.MaxTitleLength))},
		},
		{
			name: "author over the length limit",
			in:   book.Input{Title: "T", Author: strings.Repeat("x", book.MaxAuthorLength+1)},
			want: []book.FieldError{fieldErr("author", tooLong(book.MaxAuthorLength))},
		},
		{
			name: "length is counted in characters, not bytes",
			in:   book.Input{Title: strings.Repeat("é", book.MaxTitleLength), Author: "A"},
		},
		{
			name: "one character over the limit in a multi-byte title",
			in:   book.Input{Title: strings.Repeat("é", book.MaxTitleLength+1), Author: "A"},
			want: []book.FieldError{fieldErr("title", tooLong(book.MaxTitleLength))},
		},
		{name: "year 0 means unknown", in: book.Input{Title: "T", Author: "A", Year: 0}},
		{name: "highest year", in: book.Input{Title: "T", Author: "A", Year: book.MaxYear}},
		{
			name: "negative year",
			in:   book.Input{Title: "T", Author: "A", Year: -1},
			want: []book.FieldError{fieldErr("year", yearRange)},
		},
		{
			name: "year beyond the maximum",
			in:   book.Input{Title: "T", Author: "A", Year: book.MaxYear + 1},
			want: []book.FieldError{fieldErr("year", yearRange)},
		},
		{
			name: "isbn at the length limit",
			in:   book.Input{Title: "T", Author: "A", ISBN: strings.Repeat("9", book.MaxISBNLength)},
		},
		{
			name: "isbn over the length limit",
			in:   book.Input{Title: "T", Author: "A", ISBN: strings.Repeat("9", book.MaxISBNLength+1)},
			want: []book.FieldError{fieldErr("isbn", tooLong(book.MaxISBNLength))},
		},
		{
			name: "isbn is free-form text",
			in:   book.Input{Title: "T", Author: "A", ISBN: "978-0-13-468599-1 (2nd ed.)"},
		},
		{
			name: "NUL in title",
			in:   book.Input{Title: "bad\x00title", Author: "A"},
			want: []book.FieldError{fieldErr("title", control)},
		},
		{
			name: "newline in author",
			in:   book.Input{Title: "T", Author: "Two\nLines"},
			want: []book.FieldError{fieldErr("author", control)},
		},
		{
			name: "tab in isbn",
			in:   book.Input{Title: "T", Author: "A", ISBN: "123\t456"},
			want: []book.FieldError{fieldErr("isbn", control)},
		},
		{
			name: "every problem is reported, in field order",
			in: book.Input{
				Title:  "",
				Author: strings.Repeat("x", book.MaxAuthorLength+1),
				Year:   -1,
				ISBN:   strings.Repeat("9", book.MaxISBNLength+1),
			},
			want: []book.FieldError{
				fieldErr("title", required),
				fieldErr("author", tooLong(book.MaxAuthorLength)),
				fieldErr("year", yearRange),
				fieldErr("isbn", tooLong(book.MaxISBNLength)),
			},
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
			var verr *book.ValidationError
			if !errors.As(err, &verr) {
				t.Fatalf("Validate() = %v (%T), want a *book.ValidationError", err, err)
			}
			if !slices.Equal(verr.Fields, tt.want) {
				t.Errorf("Validate() fields = %+v, want %+v", verr.Fields, tt.want)
			}
		})
	}
}

func TestValidationErrorMessageNamesEveryField(t *testing.T) {
	err := book.Input{Year: -1}.Validate()
	want := "title is required; author is required; year must be between 0 and 9999"
	if err == nil || err.Error() != want {
		t.Errorf("Validate() = %v, want %q", err, want)
	}
}

func TestNormalizeTrimsTextFields(t *testing.T) {
	in := book.Input{Title: "  The Title\t", Author: "\n An Author ", Year: 1999, ISBN: " 123 "}
	got := in.Normalize()
	want := book.Input{Title: "The Title", Author: "An Author", Year: 1999, ISBN: "123"}
	if got != want {
		t.Errorf("Normalize() = %+v, want %+v", got, want)
	}
	if in.Title != "  The Title\t" {
		t.Errorf("Normalize modified its receiver: %+v", in)
	}
}

func TestNormalizeKeepsInnerWhitespace(t *testing.T) {
	got := book.Input{Title: "  A  B  ", Author: "C"}.Normalize()
	if got.Title != "A  B" {
		t.Errorf("Title = %q, want inner spacing preserved", got.Title)
	}
}

func TestNormalizedWhitespaceOnlyTitleIsRejected(t *testing.T) {
	in := book.Input{Title: "   ", Author: "A"}.Normalize()
	if in.Title != "" {
		t.Fatalf("Title = %q, want empty after normalizing", in.Title)
	}
	if err := in.Validate(); err == nil {
		t.Error("Validate() = nil, want a required-title error")
	}
}

func TestNormalizeEmptiesTextWithNothingVisible(t *testing.T) {
	got := book.Input{
		Title:  zeroWidthSpace + " ",
		Author: byteOrderMark,
		Year:   1999,
		ISBN:   wordJoiner + zeroWidthJoiner,
	}.Normalize()
	if want := (book.Input{Year: 1999}); got != want {
		t.Errorf("Normalize() = %+v, want %+v", got, want)
	}

	// Format characters inside real text are kept.
	persian := "می" + zeroWidthNonJoiner + "خواهم"
	if got := (book.Input{Title: " " + persian + " ", Author: "A"}).Normalize(); got.Title != persian {
		t.Errorf("Title = %q, want %q", got.Title, persian)
	}
}
