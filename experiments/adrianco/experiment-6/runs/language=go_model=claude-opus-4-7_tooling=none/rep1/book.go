package main

import "strings"

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func (b *bookInput) validate() []string {
	var errs []string
	if strings.TrimSpace(b.Title) == "" {
		errs = append(errs, "title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		errs = append(errs, "author is required")
	}
	return errs
}
