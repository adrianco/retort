// Package book defines the book domain model and the rules its data must obey.
package book

import (
	"errors"
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"
)

// Limits enforced by Input.Validate. Lengths are counted in characters, not bytes.
const (
	MaxTitleLength  = 255
	MaxAuthorLength = 255
	MaxISBNLength   = 32
	MinYear         = 0 // 0 means the year is unknown
	MaxYear         = 9999
)

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Input is the part of a book that clients supply. Title and author are
// required; a year of 0 and an empty ISBN mean "unknown".
type Input struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Book is a stored book: an Input plus the identifier assigned to it.
type Book struct {
	ID int64 `json:"id"`
	Input
}

// Normalize returns a copy of in with surrounding whitespace trimmed from its
// text fields. A field with nothing visible in it (see isBlank) becomes empty.
func (in Input) Normalize() Input {
	in.Title = cleanText(in.Title)
	in.Author = cleanText(in.Author)
	in.ISBN = cleanText(in.ISBN)
	return in
}

// cleanText trims surrounding white space, and reduces text that shows nothing
// to the empty string.
func cleanText(s string) string {
	if isBlank(s) {
		return ""
	}
	return strings.TrimSpace(s)
}

// Validate checks in against the rules for a book. It returns nil, or a
// *ValidationError that lists every rule that was broken.
func (in Input) Validate() error {
	var v ValidationError
	v.checkText("title", in.Title, MaxTitleLength, true)
	v.checkText("author", in.Author, MaxAuthorLength, true)
	if in.Year < MinYear || in.Year > MaxYear {
		v.add("year", fmt.Sprintf("must be between %d and %d", MinYear, MaxYear))
	}
	v.checkText("isbn", in.ISBN, MaxISBNLength, false)
	if len(v.Fields) > 0 {
		return &v
	}
	return nil
}

// FieldError describes why a single field was rejected.
type FieldError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

// ValidationError reports every field of an Input that broke a rule, in the
// order the fields are declared.
type ValidationError struct {
	Fields []FieldError
}

func (e *ValidationError) Error() string {
	msgs := make([]string, len(e.Fields))
	for i, f := range e.Fields {
		msgs[i] = f.Field + " " + f.Message
	}
	return strings.Join(msgs, "; ")
}

func (e *ValidationError) add(field, message string) {
	e.Fields = append(e.Fields, FieldError{Field: field, Message: message})
}

// checkText records at most one problem with a text field. Control characters
// (NUL, newlines, escape sequences...) are never valid in these fields.
func (e *ValidationError) checkText(field, value string, limit int, required bool) {
	switch {
	case required && isBlank(value):
		e.add(field, "is required")
	case utf8.RuneCountInString(value) > limit:
		e.add(field, fmt.Sprintf("must be at most %d characters", limit))
	case strings.ContainsFunc(value, unicode.IsControl):
		e.add(field, "must not contain control characters")
	}
}

// isBlank reports whether s shows nothing to a reader: it is empty or made up
// only of white space, invisible format characters such as U+200B (zero-width
// space), and U+FFFD, which is what invalid UTF-8 decodes to. Format characters
// inside real text are fine; Persian and Indic scripts, for one, need U+200C
// and U+200D.
func isBlank(s string) bool {
	return strings.IndexFunc(s, func(r rune) bool {
		return !unicode.IsSpace(r) && !unicode.Is(unicode.Cf, r) && r != utf8.RuneError
	}) < 0
}
