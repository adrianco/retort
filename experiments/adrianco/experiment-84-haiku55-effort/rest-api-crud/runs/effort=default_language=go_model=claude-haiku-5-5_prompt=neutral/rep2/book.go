package main

import "strings"

// maxYear is the largest publication year accepted by the API.
const maxYear = 9999

// Book is a book in the collection, as returned by the API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the request body accepted by POST /books and PUT /books/{id}.
// Year 0 means "not provided"; ISBN "" means "not provided".
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// normalize trims surrounding whitespace from the text fields so that
// validation and storage both see the cleaned values.
func (in *BookInput) normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// Validate returns a map of field name to problem description. An empty map
// means the input is valid.
func (in BookInput) Validate() map[string]string {
	problems := map[string]string{}
	if strings.TrimSpace(in.Title) == "" {
		problems["title"] = "title is required"
	}
	if strings.TrimSpace(in.Author) == "" {
		problems["author"] = "author is required"
	}
	if in.Year != 0 && (in.Year < 1 || in.Year > maxYear) {
		problems["year"] = "year must be between 1 and 9999"
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		problems["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
	}
	return problems
}

// validISBN reports whether s is a well-formed ISBN-10 or ISBN-13 with a
// correct check digit. Hyphens and spaces are ignored.
func validISBN(s string) bool {
	clean := strings.NewReplacer("-", "", " ", "").Replace(s)
	switch len(clean) {
	case 10:
		sum := 0
		for i := 0; i < 10; i++ {
			c := clean[i]
			var v int
			switch {
			case c >= '0' && c <= '9':
				v = int(c - '0')
			case c == 'X' && i == 9:
				v = 10
			default:
				return false
			}
			sum += (i + 1) * v
		}
		return sum%11 == 0
	case 13:
		sum := 0
		for i := 0; i < 13; i++ {
			c := clean[i]
			if c < '0' || c > '9' {
				return false
			}
			weight := 1
			if i%2 == 1 {
				weight = 3
			}
			sum += int(c-'0') * weight
		}
		return sum%10 == 0
	}
	return false
}
