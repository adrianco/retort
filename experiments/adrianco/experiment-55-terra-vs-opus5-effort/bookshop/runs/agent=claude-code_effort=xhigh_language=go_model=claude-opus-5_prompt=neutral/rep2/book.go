package main

import (
	"encoding/json"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

// Book is a single entry in the collection, as stored and as returned to
// clients. Year and ISBN are optional: Year is a pointer so that "no year
// recorded" round-trips as JSON null instead of a misleading 0, while an
// absent ISBN is simply the empty string.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      *int      `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput is the request body for POST /books and PUT /books/{id}. Every
// field is a pointer so validation can tell "absent" from "present but
// empty" and report the difference ("title is required" vs "title must not
// be blank").
type BookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`

	// Server-managed fields are accepted and ignored, so a client can GET a
	// book, change a field and PUT the whole document back. Unknown fields
	// are rejected (see API.decodeBook), which would otherwise make that
	// natural round trip fail. json.RawMessage accepts any shape.
	IgnoredID        json.RawMessage `json:"id"`
	IgnoredCreatedAt json.RawMessage `json:"created_at"`
	IgnoredUpdatedAt json.RawMessage `json:"updated_at"`
}

// FieldError describes one rejected field. Errors are collected rather than
// returned one at a time so a client can fix a whole form in one round trip.
type FieldError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

const (
	maxTitleLen  = 512
	maxAuthorLen = 256
	// minYear predates the printing press, so hand-copied volumes are
	// accepted while obvious typos ("year": 12) are not.
	minYear = 1000
)

// Validate normalises the input and returns the resulting Book together with
// any field errors. Because PUT replaces a book wholesale, both endpoints
// share these rules: title and author are always required, year and ISBN are
// always optional.
//
// The returned Book has no ID or timestamps; the store assigns those.
func (in BookInput) Validate(now time.Time) (Book, []FieldError) {
	var (
		b    Book
		errs []FieldError
	)

	switch {
	case in.Title == nil:
		errs = append(errs, FieldError{"title", "is required"})
	default:
		title := strings.TrimSpace(*in.Title)
		switch {
		case title == "":
			errs = append(errs, FieldError{"title", "must not be blank"})
		case utf8.RuneCountInString(title) > maxTitleLen:
			errs = append(errs, FieldError{"title", "must be at most 512 characters"})
		default:
			b.Title = title
		}
	}

	switch {
	case in.Author == nil:
		errs = append(errs, FieldError{"author", "is required"})
	default:
		author := strings.TrimSpace(*in.Author)
		switch {
		case author == "":
			errs = append(errs, FieldError{"author", "must not be blank"})
		case utf8.RuneCountInString(author) > maxAuthorLen:
			errs = append(errs, FieldError{"author", "must be at most 256 characters"})
		default:
			b.Author = author
		}
	}

	if in.Year != nil {
		// One year of slack: books are routinely catalogued ahead of
		// their official publication date.
		maxYear := now.UTC().Year() + 1
		if *in.Year < minYear || *in.Year > maxYear {
			errs = append(errs, FieldError{"year", "must be between 1000 and " + strconv.Itoa(maxYear)})
		} else {
			year := *in.Year
			b.Year = &year
		}
	}

	if in.ISBN != nil && strings.TrimSpace(*in.ISBN) != "" {
		isbn, ok := NormalizeISBN(*in.ISBN)
		if !ok {
			errs = append(errs, FieldError{"isbn", "must be a valid ISBN-10 or ISBN-13"})
		} else {
			b.ISBN = isbn
		}
	}

	if len(errs) > 0 {
		return Book{}, errs
	}
	return b, nil
}

// NormalizeISBN strips the separators an ISBN may legally be written with and
// verifies the check digit. It reports whether the value is a well-formed
// ISBN-10 or ISBN-13 and, if so, returns the canonical separator-free form so
// that "0-306-40615-2" and "0306406152" collide on the uniqueness index.
func NormalizeISBN(s string) (string, bool) {
	var digits []byte
	for i := 0; i < len(s); i++ {
		switch c := s[i]; {
		case c >= '0' && c <= '9':
			digits = append(digits, c)
		case c == 'X' || c == 'x':
			digits = append(digits, 'X')
		case c == '-' || c == ' ':
			// Separators carry no information; ISBNs are commonly
			// written with either.
		default:
			return "", false
		}
	}

	switch len(digits) {
	case 10:
		// Weights 10..1 over the ten characters; only the check digit
		// may be the value 10, written 'X'.
		sum := 0
		for i, c := range digits {
			var v int
			switch {
			case c == 'X':
				if i != 9 {
					return "", false
				}
				v = 10
			default:
				v = int(c - '0')
			}
			sum += (10 - i) * v
		}
		if sum%11 != 0 {
			return "", false
		}
	case 13:
		// Alternating weights 1 and 3; 'X' is not a legal ISBN-13
		// character anywhere, including the check digit.
		sum := 0
		for i, c := range digits {
			if c == 'X' {
				return "", false
			}
			w := 1
			if i%2 == 1 {
				w = 3
			}
			sum += w * int(c-'0')
		}
		if sum%10 != 0 {
			return "", false
		}
	default:
		return "", false
	}

	return string(digits), true
}
