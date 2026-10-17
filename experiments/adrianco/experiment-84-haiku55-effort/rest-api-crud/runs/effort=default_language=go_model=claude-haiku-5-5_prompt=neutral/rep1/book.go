package main

import (
	"strconv"
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

// BookInput is the writable part of a Book, used for create and update requests.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Normalize trims surrounding whitespace from text fields.
func (in BookInput) Normalize() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
	return in
}

// Validate returns a map of field name to problem description, or nil if the input is valid.
// Title and author are required. Year is optional but must be plausible when given.
// ISBN is optional but must be a valid ISBN-10 or ISBN-13 when given.
func (in BookInput) Validate() map[string]string {
	problems := map[string]string{}

	if in.Title == "" {
		problems["title"] = "is required"
	}
	if in.Author == "" {
		problems["author"] = "is required"
	}
	maxYear := time.Now().Year() + 1
	if in.Year != 0 && (in.Year < 1450 || in.Year > maxYear) {
		problems["year"] = "must be between 1450 and " + strconv.Itoa(maxYear)
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		problems["isbn"] = "must be a valid ISBN-10 or ISBN-13"
	}

	if len(problems) == 0 {
		return nil
	}
	return problems
}

// validISBN accepts ISBN-10 (last character may be X) and ISBN-13, with optional hyphens or spaces.
func validISBN(s string) bool {
	var digits []rune
	for _, r := range s {
		switch {
		case r == '-' || r == ' ':
			continue
		case unicode.IsDigit(r):
			digits = append(digits, r)
		case (r == 'X' || r == 'x') && len(digits) == 9:
			digits = append(digits, 'X')
		default:
			return false
		}
	}

	switch len(digits) {
	case 10:
		return isbn10Checksum(digits)
	case 13:
		return isbn13Checksum(digits)
	default:
		return false
	}
}

func isbn10Checksum(d []rune) bool {
	sum := 0
	for i := 0; i < 10; i++ {
		v := 0
		if d[i] == 'X' {
			if i != 9 {
				return false
			}
			v = 10
		} else {
			v = int(d[i] - '0')
		}
		sum += v * (10 - i)
	}
	return sum%11 == 0
}

func isbn13Checksum(d []rune) bool {
	sum := 0
	for i := 0; i < 13; i++ {
		v := int(d[i] - '0')
		if i%2 == 1 {
			v *= 3
		}
		sum += v
	}
	return sum%10 == 0
}
