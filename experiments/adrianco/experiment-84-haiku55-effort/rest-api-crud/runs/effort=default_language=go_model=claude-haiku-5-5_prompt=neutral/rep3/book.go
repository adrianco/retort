package main

import (
	"errors"
	"strings"
	"unicode"
)

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the writable part of a Book, as received from clients.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationErrors maps a field name to a human-readable problem.
type ValidationErrors map[string]string

func (v ValidationErrors) Error() string {
	return "validation failed"
}

// normalize trims whitespace from text fields and canonicalises the ISBN.
func (in BookInput) normalize() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = normalizeISBN(in.ISBN)
	return in
}

// Validate returns a ValidationErrors value describing every invalid field,
// or nil when the input is acceptable. The input should already be normalized.
//
// Rules:
//   - title and author are required
//   - year is optional: 0 means unknown, otherwise it must be in 1000..9999
//   - isbn is optional: when present it must be a valid ISBN-10 or ISBN-13
//     format (checksum is not verified)
func (in BookInput) Validate() error {
	errs := ValidationErrors{}

	if in.Title == "" {
		errs["title"] = "title is required"
	}
	if in.Author == "" {
		errs["author"] = "author is required"
	}
	if in.Year != 0 && (in.Year < 1000 || in.Year > 9999) {
		errs["year"] = "year must be 0 (unknown) or between 1000 and 9999"
	}
	if in.ISBN != "" && !isValidISBN(in.ISBN) {
		errs["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
	}

	if len(errs) == 0 {
		return nil
	}
	return errs
}

// normalizeISBN strips hyphens and spaces and upper-cases the check character.
func normalizeISBN(s string) string {
	var b strings.Builder
	for _, r := range strings.TrimSpace(s) {
		switch {
		case r == '-' || unicode.IsSpace(r):
			continue
		case r == 'x':
			b.WriteRune('X')
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

// isValidISBN checks the format of an already-normalized ISBN.
func isValidISBN(s string) bool {
	switch len(s) {
	case 10:
		for i := 0; i < 9; i++ {
			if !isDigit(s[i]) {
				return false
			}
		}
		return isDigit(s[9]) || s[9] == 'X'
	case 13:
		for i := 0; i < 13; i++ {
			if !isDigit(s[i]) {
				return false
			}
		}
		return true
	default:
		return false
	}
}

func isDigit(c byte) bool { return c >= '0' && c <= '9' }

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// ErrISBNConflict is returned when another book already has the same ISBN.
var ErrISBNConflict = errors.New("a book with this isbn already exists")
