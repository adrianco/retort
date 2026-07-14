package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Store wraps the database access for books.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at dsn and applies the schema.
func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *Store) migrate() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id     INTEGER PRIMARY KEY AUTOINCREMENT,
			title  TEXT NOT NULL,
			author TEXT NOT NULL,
			year   INTEGER NOT NULL DEFAULT 0,
			isbn   TEXT NOT NULL DEFAULT ''
		)
	`)
	return err
}

// Close releases the underlying database handle.
func (s *Store) Close() error {
	return s.db.Close()
}

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(in bookInput) (Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN,
	)
	if err != nil {
		return Book{}, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, err
	}
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// List returns all books, optionally filtered by author.
func (s *Store) List(author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author = ?`
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

// Get returns a single book by ID, or ErrNotFound.
func (s *Store) Get(id int64) (Book, error) {
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

// Update replaces the fields of an existing book. Returns ErrNotFound if missing.
func (s *Store) Update(id int64, in bookInput) (Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id,
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
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// Delete removes a book by ID. Returns ErrNotFound if missing.
func (s *Store) Delete(id int64) error {
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
