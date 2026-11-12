package main

import "time"

// Book represents a book in the collection.
type Book struct {
	ID       int64     `json:"id"`
	Title    string    `json:"title"`
	Author   string    `json:"author"`
	Year     int       `json:"year"`
	ISBN     string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}
