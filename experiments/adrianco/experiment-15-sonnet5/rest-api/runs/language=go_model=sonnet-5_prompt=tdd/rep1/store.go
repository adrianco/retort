package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a requested book does not exist.
var ErrNotFound = errors.New("book not found")

// Store provides persistence for books backed by SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) a SQLite database at the given path and
// ensures the schema exists.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}

	const schema = `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, err
	}

	return &Store{db: db}, nil
}

// Close closes the underlying database connection.
func (s *Store) Close() error {
	return s.db.Close()
}

// CreateBook inserts a new book and returns it with its assigned ID.
func (s *Store) CreateBook(b Book) (Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return Book{}, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, err
	}
	b.ID = id
	return b, nil
}

// GetBook retrieves a single book by ID, or ErrNotFound if it does not exist.
func (s *Store) GetBook(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, err
	}
	return b, nil
}

// ListBooks returns all books, optionally filtered by exact author match.
func (s *Store) ListBooks(author string) ([]Book, error) {
	var rows *sql.Rows
	var err error
	if author == "" {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
	} else {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`, author)
	}
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
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return books, nil
}

// UpdateBook replaces the fields of an existing book, returning the updated
// book or ErrNotFound if it does not exist.
func (s *Store) UpdateBook(id int64, b Book) (Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return Book{}, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, err
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	b.ID = id
	return b, nil
}

// DeleteBook removes a book by ID, or returns ErrNotFound if it does not exist.
func (s *Store) DeleteBook(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
