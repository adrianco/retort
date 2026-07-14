package main

// Book represents a single book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the payload accepted on create/update requests.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate checks the required-field constraints. It returns a human readable
// error message and false when the input is invalid.
func (in BookInput) validate() (string, bool) {
	if in.Title == "" {
		return "title is required", false
	}
	if in.Author == "" {
		return "author is required", false
	}
	return "", true
}
