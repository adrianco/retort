package main

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type CreateBookRequest struct {
	Title  string `json:"title" validate:"required,min=1"`
	Author string `json:"author" validate:"required,min=1"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type UpdateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookRepository interface {
	Create(book *Book) error
	GetByID(id int) (*Book, error)
	List(filters map[string]string) ([]*Book, error)
	Update(book *Book) error
	Delete(id int) error
}
