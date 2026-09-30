// Package book defines the book model shared by the storage and HTTP layers,
// along with input validation.
package book

import (
	"errors"
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

// Field length and value limits enforced by Input.Clean.
const (
	MaxTitleLen  = 500
	MaxAuthorLen = 255
	MaxISBNLen   = 32
	MaxYear      = 9999
)

// ErrNotFound is returned by stores when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Book is a stored book.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Input is the client-supplied representation of a book, used for both
// creating and replacing one. Year 0 and an empty ISBN mean "unknown".
type Input struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError maps field names to human-readable problems.
type ValidationError map[string]string

func (e ValidationError) Error() string {
	fields := make([]string, 0, len(e))
	for f := range e {
		fields = append(fields, f)
	}
	sort.Strings(fields)
	parts := make([]string, len(fields))
	for i, f := range fields {
		parts[i] = fmt.Sprintf("%s %s", f, e[f])
	}
	return "validation failed: " + strings.Join(parts, "; ")
}

// Clean returns a copy of the input with surrounding whitespace trimmed. It
// returns a ValidationError if title or author is blank, or if any field
// violates its limits.
func (in Input) Clean() (Input, error) {
	out := Input{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}
	problems := ValidationError{}

	switch {
	case out.Title == "":
		problems["title"] = "is required"
	case utf8.RuneCountInString(out.Title) > MaxTitleLen:
		problems["title"] = fmt.Sprintf("must be at most %d characters", MaxTitleLen)
	}
	switch {
	case out.Author == "":
		problems["author"] = "is required"
	case utf8.RuneCountInString(out.Author) > MaxAuthorLen:
		problems["author"] = fmt.Sprintf("must be at most %d characters", MaxAuthorLen)
	}
	if out.Year < 0 || out.Year > MaxYear {
		problems["year"] = fmt.Sprintf("must be between 0 and %d", MaxYear)
	}
	if utf8.RuneCountInString(out.ISBN) > MaxISBNLen {
		problems["isbn"] = fmt.Sprintf("must be at most %d characters", MaxISBNLen)
	}

	if len(problems) > 0 {
		return Input{}, problems
	}
	return out, nil
}
