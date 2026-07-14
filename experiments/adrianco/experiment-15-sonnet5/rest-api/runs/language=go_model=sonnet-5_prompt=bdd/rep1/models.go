package main

// Book represents a single book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate checks that required fields are present.
func (b Book) Validate() []string {
	var errs []string
	if b.Title == "" {
		errs = append(errs, "title is required")
	}
	if b.Author == "" {
		errs = append(errs, "author is required")
	}
	return errs
}
