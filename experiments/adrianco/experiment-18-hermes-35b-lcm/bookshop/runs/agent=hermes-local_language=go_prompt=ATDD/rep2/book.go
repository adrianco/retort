package main

import "fmt"

// Book represents a book in the collection.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookValidationErrors holds validation errors for a Book.
type BookValidationErrors struct {
	Title  string
	Author string
}

func (e *BookValidationErrors) Error() string {
	var parts []string
	if e.Title != "" {
		parts = append(parts, fmt.Sprintf("title: %s", e.Title))
	}
	if e.Author != "" {
		parts = append(parts, fmt.Sprintf("author: %s", e.Author))
	}
	return fmt.Sprintf("validation failed: %s", parts)
}

// Validate returns validation errors. Title and author must be non-empty.
func (b *Book) Validate() error {
	var errs BookValidationErrors
	if b.Title == "" {
		errs.Title = "title is required"
	}
	if b.Author == "" {
		errs.Author = "author is required"
	}
	if errs.Title != "" || errs.Author != "" {
		return &errs
	}
	return nil
}
