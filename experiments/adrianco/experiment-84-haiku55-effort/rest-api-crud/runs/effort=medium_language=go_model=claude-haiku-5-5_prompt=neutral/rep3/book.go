package main

import (
	"fmt"
	"strings"
	"time"
)

// Book is a book as stored and returned by the API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the writable part of a book, used as the body of POST and PUT.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// normalize trims surrounding whitespace and reduces the ISBN to bare digits
// (plus a trailing X for ISBN-10), so "978-0-13-468599-1" and "9780134685991"
// are treated as the same book.
func (in BookInput) normalize() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.ToUpper(strings.Map(func(r rune) rune {
		if r == '-' || r == ' ' {
			return -1
		}
		return r
	}, in.ISBN))
	return in
}

// validate returns a map of field name to problem. An empty map means valid.
// Title and author are required. Year and ISBN are optional; a zero year means
// "unknown".
func (in BookInput) validate(now time.Time) map[string]string {
	errs := map[string]string{}
	if in.Title == "" {
		errs["title"] = "title is required"
	}
	if in.Author == "" {
		errs["author"] = "author is required"
	}
	maxYear := now.Year() + 1
	if in.Year != 0 && (in.Year < 1 || in.Year > maxYear) {
		errs["year"] = fmt.Sprintf("year must be between 1 and %d", maxYear)
	}
	if in.ISBN != "" && !isValidISBN(in.ISBN) {
		errs["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
	}
	return errs
}

// isValidISBN checks a normalized ISBN string (digits only, optional final X
// for ISBN-10) including its check digit.
func isValidISBN(s string) bool {
	switch len(s) {
	case 10:
		return isValidISBN10(s)
	case 13:
		return isValidISBN13(s)
	default:
		return false
	}
}

func isValidISBN10(s string) bool {
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

func isValidISBN13(s string) bool {
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
