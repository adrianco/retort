package main

import (
	"strings"
	"time"
)

// Book is a single record in the collection.
type Book struct {
	ID        int64  `json:"id"`
	Title     string `json:"title"`
	Author    string `json:"author"`
	Year      int    `json:"year"`
	ISBN      string `json:"isbn"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

// BookInput is the client-supplied payload for create and update.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// minYear is the earliest year we accept; a zero year means "unknown" and is allowed.
const minYear = 1400

// Normalize trims incidental whitespace and canonicalizes the ISBN so that
// validation and the uniqueness constraint operate on a stable form.
func (in *BookInput) Normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = normalizeISBN(in.ISBN)
}

// Validate reports per-field problems. An empty map means the input is valid.
func (in BookInput) Validate() map[string]string {
	problems := map[string]string{}

	switch {
	case in.Title == "":
		problems["title"] = "title is required"
	case len(in.Title) > 500:
		problems["title"] = "title must be at most 500 characters"
	}

	switch {
	case in.Author == "":
		problems["author"] = "author is required"
	case len(in.Author) > 500:
		problems["author"] = "author must be at most 500 characters"
	}

	maxYear := time.Now().UTC().Year() + 1
	if in.Year != 0 && (in.Year < minYear || in.Year > maxYear) {
		problems["year"] = "year must be 0 (unknown) or between 1400 and next year"
	}

	if in.ISBN != "" && !validISBN(in.ISBN) {
		problems["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
	}

	return problems
}

// normalizeISBN strips the separators publishers use (spaces, hyphens) and
// upper-cases the ISBN-10 check character.
func normalizeISBN(raw string) string {
	var b strings.Builder
	for _, r := range raw {
		switch {
		case r >= '0' && r <= '9':
			b.WriteRune(r)
		case r == 'x' || r == 'X':
			b.WriteRune('X')
		case r == '-' || r == ' ':
			// separator, drop it
		default:
			// Keep anything unexpected so validation can reject it.
			b.WriteRune(r)
		}
	}
	return b.String()
}

// validISBN checks length and the check digit for a normalized ISBN.
func validISBN(isbn string) bool {
	switch len(isbn) {
	case 10:
		return validISBN10(isbn)
	case 13:
		return validISBN13(isbn)
	default:
		return false
	}
}

func validISBN10(isbn string) bool {
	sum := 0
	for i, r := range isbn {
		var v int
		switch {
		case r >= '0' && r <= '9':
			v = int(r - '0')
		case r == 'X' && i == 9: // only the final character may be X
			v = 10
		default:
			return false
		}
		sum += v * (10 - i)
	}
	return sum%11 == 0
}

func validISBN13(isbn string) bool {
	sum := 0
	for i, r := range isbn {
		if r < '0' || r > '9' {
			return false
		}
		v := int(r - '0')
		if i%2 == 1 {
			v *= 3
		}
		sum += v
	}
	return sum%10 == 0
}
