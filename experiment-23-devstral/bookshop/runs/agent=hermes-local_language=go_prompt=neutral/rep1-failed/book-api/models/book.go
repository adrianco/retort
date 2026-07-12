package models

// Book represents a book model
type Book struct {
    ID     int    `json:"id"`
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year"`
    ISBN   string `json:"isbn"`
}
