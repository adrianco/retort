package main

import (
	"fmt"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"
)

const (
	maxTitleLen  = 500
	maxAuthorLen = 300
)

// BookInput is the request body for creating or replacing a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Book is a stored book. Its JSON form is the input fields plus the ID.
type Book struct {
	ID int64 `json:"id"`
	BookInput
}

// ValidationError maps each invalid field name to a description of the problem.
type ValidationError map[string]string

// Normalize trims surrounding whitespace, cleans the ISBN and checks every field.
// It returns the cleaned input and a ValidationError naming each invalid field, which is
// empty when the input is acceptable.
// Title and author are required. Year is optional, with 0 meaning unknown. ISBN is optional.
func (in BookInput) Normalize() (BookInput, ValidationError) {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = cleanISBN(in.ISBN)

	problems := ValidationError{}
	switch n := utf8.RuneCountInString(in.Title); {
	case n == 0:
		problems["title"] = "title is required"
	case n > maxTitleLen:
		problems["title"] = fmt.Sprintf("title must be at most %d characters", maxTitleLen)
	}
	switch n := utf8.RuneCountInString(in.Author); {
	case n == 0:
		problems["author"] = "author is required"
	case n > maxAuthorLen:
		problems["author"] = fmt.Sprintf("author must be at most %d characters", maxAuthorLen)
	}
	if latest := time.Now().Year() + 1; in.Year != 0 && (in.Year < 1 || in.Year > latest) {
		problems["year"] = fmt.Sprintf("year must be between 1 and %d", latest)
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		problems["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
	}

	return in, problems
}

// cleanISBN removes spaces and hyphens and upper-cases the ISBN-10 check character "x".
func cleanISBN(s string) string {
	return strings.ToUpper(strings.Map(func(r rune) rune {
		if r == '-' || unicode.IsSpace(r) {
			return -1
		}
		return r
	}, s))
}

// validISBN reports whether s, already cleaned, is a valid ISBN-10 or ISBN-13.
func validISBN(s string) bool {
	switch len(s) {
	case 10:
		return validISBN10(s)
	case 13:
		return validISBN13(s)
	}
	return false
}

func validISBN10(s string) bool {
	sum := 0
	for i := range 9 {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
		sum += int(s[i]-'0') * (10 - i)
	}
	switch last := s[9]; {
	case last == 'X':
		sum += 10
	case last >= '0' && last <= '9':
		sum += int(last - '0')
	default:
		return false
	}
	return sum%11 == 0
}

func validISBN13(s string) bool {
	sum := 0
	for i := range 13 {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
		weight := 1
		if i%2 == 1 {
			weight = 3
		}
		sum += int(s[i]-'0') * weight
	}
	return sum%10 == 0
}
