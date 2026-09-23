package main

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type bookStore struct{ db *sql.DB }

func (s bookStore) list(author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	args := []any{}
	if author != "" {
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	query += ` ORDER BY id`
	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func (s bookStore) get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, errNotFound
	}
	return b, err
}

func (s bookStore) create(b Book) (Book, error) {
	result, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`, b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return Book{}, err
	}
	b.ID, err = result.LastInsertId()
	return b, err
}

func (s bookStore) update(id int64, b Book) (Book, error) {
	result, err := s.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`, b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		return Book{}, err
	}
	count, err := result.RowsAffected()
	if err != nil {
		return Book{}, err
	}
	if count == 0 {
		return Book{}, errNotFound
	}
	b.ID = id
	return b, nil
}

func (s bookStore) delete(id int64) error {
	result, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	count, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if count == 0 {
		return errNotFound
	}
	return nil
}

func validateBook(b Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}
