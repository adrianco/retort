// Package book defines the Book domain type and its input validation rules.
package book

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	// MaxTitleLen and MaxAuthorLen bound free-text fields (in runes).
	MaxTitleLen  = 500
	MaxAuthorLen = 300

	// minYear is the earliest publication year accepted. Years before the
	// printing press are not a realistic collection concern, and this keeps
	// obvious typos (e.g. 19999) out of the store.
	minYear = 1000
)

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError reports every invalid field at once. Details maps a JSON
// field name to a human-readable reason.
type ValidationError struct {
	Details map[string]string
}

func (e *ValidationError) Error() string {
	return "validation failed"
}

// Validate checks a book's fields and normalizes them in place: text fields
// are trimmed and the ISBN is reduced to its canonical form (digits, plus a
// trailing X for ISBN-10). It returns a *ValidationError listing all problems,
// or nil if the book is valid. Title and author are required; year and ISBN
// are optional but must be well-formed when present.
func Validate(b *Book) error {
	return validateAt(b, time.Now().Year())
}

// validateAt is Validate with the current year injected, so tests are stable.
func validateAt(b *Book, currentYear int) error {
	details := map[string]string{}

	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = normalizeISBN(b.ISBN)

	switch {
	case b.Title == "":
		details["title"] = "title is required"
	case utf8.RuneCountInString(b.Title) > MaxTitleLen:
		details["title"] = fmt.Sprintf("title must be at most %d characters", MaxTitleLen)
	}

	switch {
	case b.Author == "":
		details["author"] = "author is required"
	case utf8.RuneCountInString(b.Author) > MaxAuthorLen:
		details["author"] = fmt.Sprintf("author must be at most %d characters", MaxAuthorLen)
	}

	if b.Year != 0 && (b.Year < minYear || b.Year > currentYear+1) {
		details["year"] = fmt.Sprintf("year must be between %d and %d", minYear, currentYear+1)
	}

	if b.ISBN != "" && !validISBN(b.ISBN) {
		details["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
	}

	if len(details) > 0 {
		return &ValidationError{Details: details}
	}
	return nil
}

// normalizeISBN strips spaces and hyphens and upper-cases the check character.
func normalizeISBN(s string) string {
	var sb strings.Builder
	for _, r := range strings.TrimSpace(s) {
		switch {
		case r == ' ' || r == '-':
			continue
		case r == 'x':
			sb.WriteRune('X')
		default:
			sb.WriteRune(r)
		}
	}
	return sb.String()
}

// validISBN verifies length and check digit for ISBN-10 and ISBN-13.
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
		var v int
		switch {
		case c >= '0' && c <= '9':
			v = int(c - '0')
		case c == 'X' && i == 9:
			v = 10
		default:
			return false
		}
		sum += v * (10 - i)
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
		v := int(c - '0')
		if i%2 == 1 {
			v *= 3
		}
		sum += v
	}
	return sum%10 == 0
}
