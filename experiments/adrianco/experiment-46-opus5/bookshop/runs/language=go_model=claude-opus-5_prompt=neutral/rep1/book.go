package main

import (
	"fmt"
	"strings"
	"time"
)

// Book is a single entry in the collection.
//
// Year is 0 when the publication year is unknown, and ISBN is "" when the book
// has no ISBN recorded.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput is a validated, normalized set of book fields ready to be persisted.
type BookInput struct {
	Title  string
	Author string
	Year   int
	ISBN   string
}

// bookPayload mirrors the JSON request body. Fields are pointers so a missing
// key can be told apart from an explicit null or zero value.
type bookPayload struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

const (
	maxTitleLen  = 512
	maxAuthorLen = 256
	// minYear is deliberately permissive; it only rejects obvious nonsense.
	minYear = 1
)

// validate normalizes the payload and reports every problem it finds, so a
// client gets the full list of complaints in one round trip.
func (p bookPayload) validate(now time.Time) (BookInput, []string) {
	var (
		in       BookInput
		problems []string
	)

	title := strings.TrimSpace(deref(p.Title))
	switch {
	case title == "":
		problems = append(problems, "title is required")
	case len(title) > maxTitleLen:
		problems = append(problems, fmt.Sprintf("title must be at most %d characters", maxTitleLen))
	}
	in.Title = title

	author := strings.TrimSpace(deref(p.Author))
	switch {
	case author == "":
		problems = append(problems, "author is required")
	case len(author) > maxAuthorLen:
		problems = append(problems, fmt.Sprintf("author must be at most %d characters", maxAuthorLen))
	}
	in.Author = author

	if p.Year != nil {
		year := *p.Year
		maxYear := now.UTC().Year() + 1
		if year != 0 && (year < minYear || year > maxYear) {
			problems = append(problems, fmt.Sprintf("year must be 0 (unknown) or between %d and %d", minYear, maxYear))
		}
		in.Year = year
	}

	if p.ISBN != nil {
		isbn, err := normalizeISBN(*p.ISBN)
		if err != nil {
			problems = append(problems, err.Error())
		}
		in.ISBN = isbn
	}

	return in, problems
}

// normalizeISBN strips separators and verifies the check digit of an ISBN-10 or
// ISBN-13. An empty (or whitespace-only) input is valid and means "no ISBN".
func normalizeISBN(raw string) (string, error) {
	var b strings.Builder
	for _, r := range raw {
		switch {
		case r == '-' || r == ' ':
			// Separators are cosmetic.
		case r >= '0' && r <= '9':
			b.WriteRune(r)
		case r == 'x' || r == 'X':
			b.WriteRune('X')
		default:
			return "", fmt.Errorf("isbn contains invalid character %q", r)
		}
	}

	s := b.String()
	switch len(s) {
	case 0:
		return "", nil
	case 10:
		if !validISBN10(s) {
			return "", fmt.Errorf("isbn %q has an invalid ISBN-10 check digit", s)
		}
	case 13:
		if !validISBN13(s) {
			return "", fmt.Errorf("isbn %q has an invalid ISBN-13 check digit", s)
		}
	default:
		return "", fmt.Errorf("isbn must have 10 or 13 digits, got %d", len(s))
	}
	return s, nil
}

func validISBN10(s string) bool {
	sum := 0
	for i, r := range s {
		var d int
		switch {
		case r == 'X':
			// Only the final check digit may be X.
			if i != 9 {
				return false
			}
			d = 10
		default:
			d = int(r - '0')
		}
		sum += d * (10 - i)
	}
	return sum%11 == 0
}

func validISBN13(s string) bool {
	sum := 0
	for i, r := range s {
		if r == 'X' {
			return false
		}
		d := int(r - '0')
		if i%2 == 0 {
			sum += d
		} else {
			sum += 3 * d
		}
	}
	return sum%10 == 0
}

func deref(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}
