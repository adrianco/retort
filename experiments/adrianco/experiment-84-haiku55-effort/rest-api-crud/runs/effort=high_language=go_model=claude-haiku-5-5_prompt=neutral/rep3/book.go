// Package bookapi implements a REST API for managing a book collection,
// backed by an embedded SQLite database.
package bookapi

import (
	"strings"
	"time"
	"unicode"
)

// Book is a book as stored and returned by the API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the request body for creating or replacing a book.
// Title and Author are required. Year 0 and an empty ISBN mean "unknown".
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError maps a field name to a human-readable problem.
type ValidationError map[string]string

// Error implements the error interface.
func (v ValidationError) Error() string {
	return "validation failed"
}

// Clean returns a copy of in with whitespace trimmed from text fields and
// ISBN hyphens/spaces removed, so that validation and storage see one form.
func (in BookInput) Clean() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = cleanISBN(in.ISBN)
	return in
}

// Validate checks a cleaned BookInput. It returns nil when the input is valid,
// otherwise a ValidationError describing every invalid field.
func (in BookInput) Validate() error {
	errs := ValidationError{}

	if in.Title == "" {
		errs["title"] = "is required"
	}
	if in.Author == "" {
		errs["author"] = "is required"
	}
	if in.Year != 0 && (in.Year < 1 || in.Year > time.Now().Year()+1) {
		errs["year"] = "must be a valid publication year"
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		errs["isbn"] = "must be a valid ISBN-10 or ISBN-13"
	}

	if len(errs) == 0 {
		return nil
	}
	return errs
}

// cleanISBN strips hyphens and spaces and upper-cases the check character.
func cleanISBN(s string) string {
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

// validISBN reports whether s (already cleaned) is a valid ISBN-10 or ISBN-13,
// including the check digit.
func validISBN(s string) bool {
	switch len(s) {
	case 10:
		return validISBN10(s)
	case 13:
		return validISBN13(s)
	default:
		return false
	}
}

func validISBN10(s string) bool {
	sum := 0
	for i := 0; i < 10; i++ {
		c := s[i]
		var d int
		switch {
		case c >= '0' && c <= '9':
			d = int(c - '0')
		case c == 'X' && i == 9:
			d = 10
		default:
			return false
		}
		sum += (10 - i) * d
	}
	return sum%11 == 0
}

func validISBN13(s string) bool {
	sum := 0
	for i := 0; i < 13; i++ {
		c := s[i]
		if c < '0' || c > '9' {
			return false
		}
		weight := 1
		if i%2 == 1 {
			weight = 3
		}
		sum += int(c-'0') * weight
	}
	return sum%10 == 0
}
