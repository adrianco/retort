package main

import (
	"errors"
	"fmt"
	"strings"
	"time"
	"unicode"
)

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the client-supplied payload for create and update requests. The
// fields are pointers so that a missing key can be told apart from an empty
// value, which lets validation report "title is required" for both cases.
type BookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// ErrValidation wraps all input problems so handlers can map them to 400.
var ErrValidation = errors.New("validation failed")

// validationError carries the per-field messages returned to the client.
type validationError struct {
	Fields map[string]string
}

func (e *validationError) Error() string {
	parts := make([]string, 0, len(e.Fields))
	for field, msg := range e.Fields {
		parts = append(parts, field+": "+msg)
	}
	return "validation failed (" + strings.Join(parts, "; ") + ")"
}

func (e *validationError) Is(target error) bool { return target == ErrValidation }

// Validate normalises the input and turns it into a Book. The returned Book has
// no ID; callers assign one when inserting.
func (in BookInput) Validate() (Book, error) {
	fields := map[string]string{}
	var b Book

	b.Title = deref(in.Title)
	if b.Title == "" {
		fields["title"] = "is required"
	} else if len(b.Title) > 500 {
		fields["title"] = "must be at most 500 characters"
	}

	b.Author = deref(in.Author)
	if b.Author == "" {
		fields["author"] = "is required"
	} else if len(b.Author) > 500 {
		fields["author"] = "must be at most 500 characters"
	}

	// Year is optional; 0 means "unknown". Anything else has to be plausible.
	if in.Year != nil {
		b.Year = *in.Year
		maxYear := time.Now().Year() + 5
		if b.Year != 0 && (b.Year < 1 || b.Year > maxYear) {
			fields["year"] = fmt.Sprintf("must be between 1 and %d", maxYear)
		}
	}

	// ISBN is optional, but a supplied one must look like an ISBN-10 or -13.
	if in.ISBN != nil {
		isbn := normalizeISBN(*in.ISBN)
		if isbn != "" && !validISBN(isbn) {
			fields["isbn"] = "must be a 10 or 13 digit ISBN"
		}
		b.ISBN = isbn
	}

	if len(fields) > 0 {
		return Book{}, &validationError{Fields: fields}
	}
	return b, nil
}

func deref(s *string) string {
	if s == nil {
		return ""
	}
	return strings.TrimSpace(*s)
}

// normalizeISBN strips the hyphens and spaces publishers use for readability.
func normalizeISBN(s string) string {
	var sb strings.Builder
	for _, r := range s {
		if r == '-' || unicode.IsSpace(r) {
			continue
		}
		sb.WriteRune(unicode.ToUpper(r))
	}
	return sb.String()
}

// validISBN checks the shape of an already-normalised ISBN: 10 digits with an
// optional trailing X check character, or 13 digits.
func validISBN(s string) bool {
	if len(s) != 10 && len(s) != 13 {
		return false
	}
	for i, r := range s {
		if r >= '0' && r <= '9' {
			continue
		}
		if r == 'X' && len(s) == 10 && i == 9 {
			continue
		}
		return false
	}
	return true
}
