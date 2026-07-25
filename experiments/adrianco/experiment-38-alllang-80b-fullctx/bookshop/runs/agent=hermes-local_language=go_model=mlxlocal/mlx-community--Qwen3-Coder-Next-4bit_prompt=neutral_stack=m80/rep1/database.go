package main

import (
	"database/sql"
	"errors"
)

// GetBooks retrieves all books
func (db *DB) GetBooks() ([]Book, error) {
	rows, err := db.Query("SELECT id, title, author, year, isbn, created_at FROM books ORDER BY id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

// GetBooksByAuthor retrieves all books by author (case-insensitive partial match)
func (db *DB) GetBooksByAuthor(author string) ([]Book, error) {
	authorPattern := "%" + author + "%"
	rows, err := db.Query("SELECT id, title, author, year, isbn, created_at FROM books WHERE author LIKE ? ORDER BY id", authorPattern)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

// GetBook retrieves a single book by ID
func (db *DB) GetBook(id int) (*Book, error) {
	book := &Book{}
	err := db.QueryRow("SELECT id, title, author, year, isbn, created_at FROM books WHERE id = ?", id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt)
	if err != nil {
		return nil, err
	}
	return book, nil
}

// CreateBook creates a new book
func (db *DB) CreateBook(book *BookInput) (*Book, error) {
	result, err := db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN,
	)
	if err != nil {
		return nil, err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, err
	}

	return &Book{
		ID:     int(id),
		Title:  book.Title,
		Author: book.Author,
		Year:   book.Year,
		ISBN:   book.ISBN,
	}, nil
}

// UpdateBook updates an existing book
func (db *DB) UpdateBook(id int, book *BookInput) (*Book, error) {
	// First check if book exists
	var exists int
	err := db.QueryRow("SELECT COUNT(*) FROM books WHERE id = ?", id).Scan(&exists)
	if err != nil {
		return nil, err
	}
	if exists == 0 {
		return nil, errors.New("book not found")
	}

	_, err = db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, id,
	)
	if err != nil {
		return nil, err
	}

	return db.GetBook(id)
}

// DeleteBook deletes a book by ID
func (db *DB) DeleteBook(id int) error {
	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rowsAffected == 0 {
		return sql.ErrNoRows
	}
	return nil
}
