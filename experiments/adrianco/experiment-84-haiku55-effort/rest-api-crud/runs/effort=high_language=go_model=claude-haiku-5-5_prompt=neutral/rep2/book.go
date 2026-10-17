package main

import (
	"strings"
	"time"
)

// Book is a stored entry in the collection.
type Book struct {
	ID int64 `json:"id"`
	BookFields
}

// BookFields holds the client-editable attributes of a book.
type BookFields struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError maps each invalid field name to a human-readable reason.
type ValidationError map[string]string

func (ValidationError) Error() string { return "validation failed" }

// Normalize trims surrounding whitespace from the string fields.
func (f *BookFields) Normalize() {
	f.Title = strings.TrimSpace(f.Title)
	f.Author = strings.TrimSpace(f.Author)
	f.ISBN = strings.TrimSpace(f.ISBN)
}

// Validate checks the fields and returns a ValidationError listing every
// problem found, or nil if the book is acceptable. Title and author are
// required. Year and ISBN are optional; a zero year means "unknown".
func (f BookFields) Validate() error {
	errs := ValidationError{}

	if f.Title == "" {
		errs["title"] = "title is required"
	}
	if f.Author == "" {
		errs["author"] = "author is required"
	}
	if f.Year != 0 && (f.Year < 1 || f.Year > time.Now().Year()+1) {
		errs["year"] = "year must be between 1 and next year"
	}
	if f.ISBN != "" && !validISBN(f.ISBN) {
		errs["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
	}

	if len(errs) == 0 {
		return nil
	}
	return errs
}

// validISBN accepts ISBN-10 or ISBN-13 with optional hyphens or spaces and
// verifies the check digit.
func validISBN(s string) bool {
	clean := strings.Map(func(r rune) rune {
		if r == '-' || r == ' ' {
			return -1
		}
		return r
	}, s)

	switch len(clean) {
	case 10:
		return validISBN10(clean)
	case 13:
		return validISBN13(clean)
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
		sum += (10 - i) * v
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
		if i%2 == 0 {
			sum += v
		} else {
			sum += 3 * v
		}
	}
	return sum%10 == 0
}
