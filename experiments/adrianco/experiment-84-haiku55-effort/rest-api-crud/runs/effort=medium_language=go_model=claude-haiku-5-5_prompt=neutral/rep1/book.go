package main

import (
	"strconv"
	"strings"
	"time"
	"unicode"
)

// Book is a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the client-supplied representation used for create and update.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// normalize trims surrounding whitespace and strips hyphens and spaces from the ISBN
// so that the stored form is canonical.
func (in BookInput) normalize() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = normalizeISBN(in.ISBN)
	return in
}

// Validate returns a map of field name to problem description. An empty map means the
// input is valid. The input should already be normalized.
func (in BookInput) Validate() map[string]string {
	problems := map[string]string{}

	if in.Title == "" {
		problems["title"] = "is required"
	}
	if in.Author == "" {
		problems["author"] = "is required"
	}
	if maxYear := time.Now().Year() + 1; in.Year < 0 || in.Year > maxYear {
		problems["year"] = "must be between 0 and " + strconv.Itoa(maxYear)
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		problems["isbn"] = "must be a valid ISBN-10 or ISBN-13"
	}
	return problems
}

// normalizeISBN removes hyphens and spaces and upper-cases x (the ISBN-10 check character).
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

// validISBN checks the length, character set and check digit of an ISBN-10 or ISBN-13.
// The input must already be normalized by normalizeISBN.
func validISBN(s string) bool {
	switch len(s) {
	case 10:
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
	case 13:
		sum := 0
		for i := 0; i < 13; i++ {
			c := s[i]
			if c < '0' || c > '9' {
				return false
			}
			w := 1
			if i%2 == 1 {
				w = 3
			}
			sum += w * int(c-'0')
		}
		return sum%10 == 0
	default:
		return false
	}
}
