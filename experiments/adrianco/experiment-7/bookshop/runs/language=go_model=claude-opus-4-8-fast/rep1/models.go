package main

// Book represents a single book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// bookInput is the payload accepted when creating or updating a book.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate checks the required fields and returns a human-readable error
// message, or an empty string when the input is valid.
func (in bookInput) validate() string {
	if in.Title == "" {
		return "title is required"
	}
	if in.Author == "" {
		return "author is required"
	}
	return ""
}
