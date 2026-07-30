// Package books holds the book domain model, its validation rules and the
// SQLite-backed storage layer for the collection.
package books

import (
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

// Field length limits. They exist so a client cannot fill the database with a
// single multi-megabyte title.
const (
	MaxTitleLen  = 512
	MaxAuthorLen = 256
)

// MinYear is the earliest publication year the API accepts. Movable type
// predates it comfortably, so anything older is far more likely to be a typo.
const MinYear = 1

// Book is one entry in the collection.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Input is the client-supplied half of a book: the payload of a create request
// and of an update request, which replaces every field.
//
// Year and ISBN are optional; their zero values mean "unknown".
type Input struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError reports the fields of an Input that failed validation,
// keyed by their JSON name.
type ValidationError struct {
	Fields map[string]string
}

func (e *ValidationError) Error() string {
	names := make([]string, 0, len(e.Fields))
	for name := range e.Fields {
		names = append(names, name)
	}
	sort.Strings(names)

	parts := make([]string, 0, len(names))
	for _, name := range names {
		parts = append(parts, fmt.Sprintf("%s: %s", name, e.Fields[name]))
	}
	return "invalid book: " + strings.Join(parts, "; ")
}

// Validate normalises the input in place — trimming surrounding whitespace from
// the title and author, canonicalising the ISBN — and then reports every field
// that is still invalid as a *ValidationError.
//
// now bounds the publication year: a book cannot be published far in the
// future. It is a parameter rather than a call to time.Now so that the rule is
// deterministic under test.
func (in *Input) Validate(now time.Time) error {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)

	fields := make(map[string]string)

	switch {
	case in.Title == "":
		fields["title"] = "title is required"
	case utf8.RuneCountInString(in.Title) > MaxTitleLen:
		fields["title"] = fmt.Sprintf("title must be at most %d characters", MaxTitleLen)
	}

	switch {
	case in.Author == "":
		fields["author"] = "author is required"
	case utf8.RuneCountInString(in.Author) > MaxAuthorLen:
		fields["author"] = fmt.Sprintf("author must be at most %d characters", MaxAuthorLen)
	}

	maxYear := now.UTC().Year() + 1
	if in.Year != 0 && (in.Year < MinYear || in.Year > maxYear) {
		fields["year"] = fmt.Sprintf("year must be between %d and %d, or 0 if unknown", MinYear, maxYear)
	}

	if isbn, err := NormalizeISBN(in.ISBN); err != nil {
		fields["isbn"] = err.Error()
	} else {
		in.ISBN = isbn
	}

	if len(fields) > 0 {
		return &ValidationError{Fields: fields}
	}
	return nil
}
