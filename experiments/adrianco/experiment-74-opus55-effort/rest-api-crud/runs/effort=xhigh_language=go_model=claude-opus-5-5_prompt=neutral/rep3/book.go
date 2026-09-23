package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxTitleLen  = 500
	maxAuthorLen = 300
)

// Book is a stored book as returned by the API.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      *int      `json:"year"`
	ISBN      *string   `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput is the client-supplied payload for creating or replacing a book.
// Year and ISBN are optional; a missing or null value means "unknown".
type BookInput struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// ValidationError maps field names to a description of what is wrong with them.
type ValidationError map[string]string

func (v ValidationError) Error() string {
	fields := make([]string, 0, len(v))
	for f := range v {
		fields = append(fields, f)
	}
	sort.Strings(fields)
	msgs := make([]string, 0, len(fields))
	for _, f := range fields {
		msgs = append(msgs, f+": "+v[f])
	}
	return "validation failed: " + strings.Join(msgs, "; ")
}

// Normalize returns a copy of in with surrounding whitespace trimmed, an empty
// ISBN treated as absent and a valid ISBN reduced to its canonical form
// (digits only, upper-case check character). It returns a ValidationError if
// any field is invalid. now supplies the current year for the year bound.
func (in BookInput) Normalize(now time.Time) (BookInput, error) {
	out := BookInput{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
	}
	errs := ValidationError{}

	switch {
	case out.Title == "":
		errs["title"] = "is required"
	case utf8.RuneCountInString(out.Title) > maxTitleLen:
		errs["title"] = fmt.Sprintf("must be at most %d characters", maxTitleLen)
	}

	switch {
	case out.Author == "":
		errs["author"] = "is required"
	case utf8.RuneCountInString(out.Author) > maxAuthorLen:
		errs["author"] = fmt.Sprintf("must be at most %d characters", maxAuthorLen)
	}

	// Allow next year so that announced, forthcoming books can be recorded.
	if maxYear := now.Year() + 1; out.Year != nil && (*out.Year < 1 || *out.Year > maxYear) {
		errs["year"] = fmt.Sprintf("must be between 1 and %d", maxYear)
	}

	if in.ISBN != nil && strings.TrimSpace(*in.ISBN) != "" {
		if isbn, ok := normalizeISBN(*in.ISBN); ok {
			out.ISBN = &isbn
		} else {
			errs["isbn"] = "must be a valid ISBN-10 or ISBN-13"
		}
	}

	if len(errs) > 0 {
		return BookInput{}, errs
	}
	return out, nil
}

// normalizeISBN strips hyphens and spaces from s and reports whether the
// result is a valid ISBN-10 or ISBN-13, checksum included.
func normalizeISBN(s string) (string, bool) {
	s = strings.ToUpper(strings.NewReplacer("-", "", " ", "").Replace(strings.TrimSpace(s)))
	switch len(s) {
	case 10:
		return s, validISBN10(s)
	case 13:
		return s, validISBN13(s)
	default:
		return "", false
	}
}

// validISBN10 checks the mod-11 checksum; only the last character may be 'X'.
func validISBN10(s string) bool {
	sum := 0
	for i := range 10 {
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

// validISBN13 checks the EAN-13 mod-10 checksum with alternating 1/3 weights.
func validISBN13(s string) bool {
	sum := 0
	for i := range 13 {
		c := s[i]
		if c < '0' || c > '9' {
			return false
		}
		d := int(c - '0')
		if i%2 == 1 {
			d *= 3
		}
		sum += d
	}
	return sum%10 == 0
}
