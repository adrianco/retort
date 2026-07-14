package main

import "errors"

// Book represents a book in the collection.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate checks that required fields are populated.
// Returns an error if title or author is empty.
func (b *Book) Validate() error {
	if b.Title == "" {
		return errors.New("title is required")
	}
	if b.Author == "" {
		return errors.New("author is required")
	}
	return nil
}
