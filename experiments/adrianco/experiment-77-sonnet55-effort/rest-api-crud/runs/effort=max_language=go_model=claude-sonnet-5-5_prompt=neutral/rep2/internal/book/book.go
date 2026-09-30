// Package book defines the book model shared by the storage and HTTP layers,
// together with the rules a client-supplied book must satisfy.
package book

import (
	"errors"
	"fmt"
	"maps"
	"slices"
	"strings"
	"unicode/utf8"
)

// Limits enforced by Input.Validate.
const (
	MaxTextLength = 255  // title and author, in characters
	MaxISBNLength = 32   // in characters; the format itself is not checked
	MaxYear       = 9999 // valid years run from 0 ("not provided") to MaxYear
)

// ErrNotFound is returned by stores when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// Book is a stored book. Year is 0 and ISBN is empty when the client did not
// provide them.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Input is the client-controlled part of a book, as sent to create and update
// requests. It deliberately has no ID: identifiers are assigned by the store
// and an "id" in a request body is ignored.
type Input struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Normalize trims surrounding whitespace from the text fields.
func (in *Input) Normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// Validate reports every rule the input violates as a ValidationError, or nil
// if the input is acceptable. Title and author are required; year and ISBN are
// optional. Surrounding whitespace is ignored, so a title of "  " is missing.
func (in Input) Validate() error {
	errs := ValidationError{}
	requireText(errs, "title", in.Title)
	requireText(errs, "author", in.Author)

	if n := utf8.RuneCountInString(strings.TrimSpace(in.ISBN)); n > MaxISBNLength {
		errs["isbn"] = fmt.Sprintf("must be at most %d characters", MaxISBNLength)
	}
	if in.Year < 0 || in.Year > MaxYear {
		errs["year"] = fmt.Sprintf("must be between 0 and %d", MaxYear)
	}

	if len(errs) == 0 {
		return nil // not errs: a non-nil empty map would be a non-nil error
	}
	return errs
}

func requireText(errs ValidationError, field, value string) {
	n := utf8.RuneCountInString(strings.TrimSpace(value))
	switch {
	case n == 0:
		errs[field] = "is required"
	case n > MaxTextLength:
		errs[field] = fmt.Sprintf("must be at most %d characters", MaxTextLength)
	}
}

// ValidationError maps the JSON name of each rejected field to the reason it
// was rejected.
type ValidationError map[string]string

// Error lists the problems in field-name order so the message is stable.
func (e ValidationError) Error() string {
	parts := make([]string, 0, len(e))
	for _, field := range slices.Sorted(maps.Keys(e)) {
		parts = append(parts, field+" "+e[field])
	}
	return "invalid book: " + strings.Join(parts, "; ")
}
