// Package book defines the book model shared by the storage and HTTP layers,
// together with the rules an incoming book must satisfy.
package book

import (
	"errors"
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"
)

// Limits enforced by Input.Validate.
const (
	MaxTextLen = 500 // characters allowed in a title or an author
	MaxISBNLen = 32  // characters allowed in an ISBN
	MinYear    = 0
	MaxYear    = 9999
)

// ErrNotFound is returned by a store when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// Input is the client-supplied part of a book: everything except the ID.
// Title and author are required. Year and ISBN are optional, and nil means
// "not provided".
type Input struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// Book is a stored book.
type Book struct {
	ID int64 `json:"id"`
	Input
}

// Normalized returns a copy of in with surrounding whitespace trimmed and a
// blank ISBN treated as not provided. The receiver is left untouched.
func (in Input) Normalized() Input {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	if in.ISBN != nil {
		if isbn := strings.TrimSpace(*in.ISBN); isbn != "" {
			in.ISBN = &isbn
		} else {
			in.ISBN = nil
		}
	}
	return in
}

// Validate checks the normalized form of in and reports every rule it breaks
// as a ValidationError, or returns nil when the input is acceptable.
//
// Only the title and the author are mandatory. The ISBN is deliberately not
// checked for format or uniqueness: it is stored as an opaque string.
func (in Input) Validate() error {
	in = in.Normalized()
	var errs ValidationError

	if problem := textProblem(in.Title, true, MaxTextLen); problem != "" {
		errs = append(errs, FieldError{"title", problem})
	}
	if problem := textProblem(in.Author, true, MaxTextLen); problem != "" {
		errs = append(errs, FieldError{"author", problem})
	}
	if in.Year != nil && (*in.Year < MinYear || *in.Year > MaxYear) {
		errs = append(errs, FieldError{"year", fmt.Sprintf("must be between %d and %d", MinYear, MaxYear)})
	}
	if in.ISBN != nil {
		if problem := textProblem(*in.ISBN, false, MaxISBNLen); problem != "" {
			errs = append(errs, FieldError{"isbn", problem})
		}
	}

	if len(errs) > 0 {
		return errs
	}
	return nil
}

// textProblem says what is wrong with an already trimmed text field, or returns
// "" if it is acceptable. Control characters are refused, NUL above all: SQLite's
// string functions treat it as the end of the value, so a title beginning with
// one would look empty to the database.
func textProblem(s string, required bool, maxLen int) string {
	switch {
	case s == "" && required:
		return "is required"
	case utf8.RuneCountInString(s) > maxLen:
		return fmt.Sprintf("must be at most %d characters", maxLen)
	case strings.IndexFunc(s, unicode.IsControl) >= 0:
		return "must not contain control characters"
	}
	return ""
}

// FieldError describes why a single field of an Input was rejected.
type FieldError struct {
	Field   string
	Message string
}

// ValidationError lists every problem found in an Input, in field order.
type ValidationError []FieldError

// Error joins the problems into one line, e.g. "title is required; author is required".
func (e ValidationError) Error() string {
	parts := make([]string, len(e))
	for i, fe := range e {
		parts[i] = fe.Field + " " + fe.Message
	}
	return strings.Join(parts, "; ")
}
