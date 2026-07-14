package main

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// bookInput is the payload accepted on create/update.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate checks the required fields. It returns a human-readable error
// message and false when the input is invalid.
func (b bookInput) validate() (string, bool) {
	if b.Title == "" {
		return "title is required", false
	}
	if b.Author == "" {
		return "author is required", false
	}
	return "", true
}
