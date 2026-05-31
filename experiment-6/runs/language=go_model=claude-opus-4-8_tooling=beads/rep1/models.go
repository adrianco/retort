package main

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the payload accepted when creating or updating a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate checks that required fields are present.
func (in BookInput) validate() []string {
	var errs []string
	if in.Title == "" {
		errs = append(errs, "title is required")
	}
	if in.Author == "" {
		errs = append(errs, "author is required")
	}
	return errs
}
