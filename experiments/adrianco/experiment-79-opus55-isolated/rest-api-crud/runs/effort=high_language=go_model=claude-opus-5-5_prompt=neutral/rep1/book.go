package main

import "strings"

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the client-supplied payload for creating or updating a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Normalize trims surrounding whitespace from the text fields.
func (in *BookInput) Normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// Validate returns a map of field name to problem, empty when the input is
// acceptable. Call Normalize first so whitespace-only values count as missing.
func (in BookInput) Validate() map[string]string {
	problems := map[string]string{}
	if in.Title == "" {
		problems["title"] = "title is required"
	}
	if in.Author == "" {
		problems["author"] = "author is required"
	}
	if in.Year < 0 {
		problems["year"] = "year must not be negative"
	}
	return problems
}
