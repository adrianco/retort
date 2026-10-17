package main

import (
	"errors"
	"strings"
)

// Book is a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the request body for creating or replacing a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError describes which fields failed validation.
type ValidationError struct {
	Fields map[string]string
}

func (e *ValidationError) Error() string {
	parts := make([]string, 0, len(e.Fields))
	for field, msg := range e.Fields {
		parts = append(parts, field+" "+msg)
	}
	return "invalid book: " + strings.Join(parts, "; ")
}

// Normalize trims whitespace from all string fields.
func (in BookInput) Normalize() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
	return in
}

// Validate checks a normalized BookInput. Title and author are required,
// year must be non-negative, and isbn (if given) must look like an ISBN-10
// or ISBN-13 (digits, optionally a trailing X for ISBN-10, hyphens ignored).
func (in BookInput) Validate() error {
	fields := map[string]string{}
	if in.Title == "" {
		fields["title"] = "is required"
	}
	if in.Author == "" {
		fields["author"] = "is required"
	}
	if in.Year < 0 {
		fields["year"] = "must not be negative"
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		fields["isbn"] = "must be a valid ISBN-10 or ISBN-13"
	}
	if len(fields) > 0 {
		return &ValidationError{Fields: fields}
	}
	return nil
}

func validISBN(s string) bool {
	clean := strings.ReplaceAll(s, "-", "")
	switch len(clean) {
	case 10:
		for i, r := range clean {
			if r >= '0' && r <= '9' {
				continue
			}
			if r == 'X' && i == 9 {
				continue
			}
			return false
		}
		return true
	case 13:
		for _, r := range clean {
			if r < '0' || r > '9' {
				return false
			}
		}
		return true
	}
	return false
}

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")
