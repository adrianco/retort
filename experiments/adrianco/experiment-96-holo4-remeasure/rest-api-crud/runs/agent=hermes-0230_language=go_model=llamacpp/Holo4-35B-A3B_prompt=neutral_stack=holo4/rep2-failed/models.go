package main

import "time"

type Book struct {
	ID       int       `json:"id"`
	Title    string    `json:"title"`
	Author   string    `json:"author"`
	Year     int       `json:"year"`
	ISBN     string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type CreateBookRequest struct {
	Title string `json:"title"`
	Author string `json:"author"`
	Year  int    `json:"year"`
	ISBN  string `json:"isbn"`
}

type UpdateBookRequest struct {
	Title *string `json:"title"`
	Author *string `json:"author"`
	Year  *int    `json:"year"`
	ISBN  *string `json:"isbn"`
}
