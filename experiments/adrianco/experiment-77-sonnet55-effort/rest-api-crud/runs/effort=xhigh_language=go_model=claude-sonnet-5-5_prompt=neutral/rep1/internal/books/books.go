// Package books holds the book model, its validation rules and the SQLite
// store that persists it.
package books

import (
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

// Field length and value limits enforced by Input.Clean.
const (
	MaxTitleLen  = 500
	MaxAuthorLen = 200
	MaxISBNLen   = 32
	MaxYear      = 9999
)

// Book is a stored book.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Input is the client-writable part of a Book, used for create and update.
type Input struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError maps field names to what is wrong with them.
type ValidationError map[string]string

func (v ValidationError) Error() string {
	fields := make([]string, 0, len(v))
	for f := range v {
		fields = append(fields, f)
	}
	sort.Strings(fields)
	parts := make([]string, len(fields))
	for i, f := range fields {
		parts[i] = fmt.Sprintf("%s %s", f, v[f])
	}
	return "validation failed: " + strings.Join(parts, "; ")
}

// Clean trims surrounding whitespace and validates the input. Title and author
// are required; a year of 0 means "not given". It returns a ValidationError
// describing every offending field.
func (in Input) Clean() (Input, error) {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)

	problems := ValidationError{}
	switch n := utf8.RuneCountInString(in.Title); {
	case n == 0:
		problems["title"] = "is required"
	case n > MaxTitleLen:
		problems["title"] = fmt.Sprintf("must be at most %d characters", MaxTitleLen)
	}
	switch n := utf8.RuneCountInString(in.Author); {
	case n == 0:
		problems["author"] = "is required"
	case n > MaxAuthorLen:
		problems["author"] = fmt.Sprintf("must be at most %d characters", MaxAuthorLen)
	}
	if in.Year < 0 || in.Year > MaxYear {
		problems["year"] = fmt.Sprintf("must be between 0 and %d", MaxYear)
	}
	if utf8.RuneCountInString(in.ISBN) > MaxISBNLen {
		problems["isbn"] = fmt.Sprintf("must be at most %d characters", MaxISBNLen)
	}

	if len(problems) > 0 {
		return Input{}, problems
	}
	return in, nil
}
