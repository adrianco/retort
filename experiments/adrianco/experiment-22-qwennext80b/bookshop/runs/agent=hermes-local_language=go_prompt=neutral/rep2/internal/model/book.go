package model

import (
	"database/sql"
	"errors"
	"time"
)

type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore(db *sql.DB) *BookStore {
	return &BookStore{db: db}
}

func (s *BookStore) CreateBook(book *Book) error {
	query := `INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`
	result, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, time.Now(), time.Now())
	if err != nil {
		return err
	}
	id, err := result.LastInsertId()
	if err != nil {
		return err
	}
	book.ID = id
	return nil
}

func (s *BookStore) GetBook(id int64) (*Book, error) {
	book := &Book{}
	query := `SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`
	err := s.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, errors.New("book not found")
		}
		return nil, err
	}
	return book, nil
}

func (s *BookStore) GetBooksByAuthor(author string) ([]*Book, error) {
	query := `SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ?`
	rows, err := s.db.Query(query, author)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		book := &Book{}
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt); err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

func (s *BookStore) GetAllBooks() ([]*Book, error) {
	query := `SELECT id, title, author, year, isbn, created_at, updated_at FROM books`
	rows, err := s.db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		book := &Book{}
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt); err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

func (s *BookStore) UpdateBook(id int64, book *Book) error {
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?`
	_, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, time.Now(), id)
	if err != nil {
		return err
	}
	return nil
}

func (s *BookStore) DeleteBook(id int64) error {
	query := `DELETE FROM books WHERE id = ?`
	_, err := s.db.Exec(query, id)
	if err != nil {
		return err
	}
	return nil
}
