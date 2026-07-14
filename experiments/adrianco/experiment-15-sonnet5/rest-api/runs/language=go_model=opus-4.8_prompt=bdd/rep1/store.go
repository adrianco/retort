package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Store provides persistence for books backed by SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) a SQLite database at dsn and ensures the schema
// exists. Use ":memory:" for an in-memory database.
func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	// An in-memory database lives only as long as a single connection, so pin
	// the pool to one connection to keep the data stable across queries.
	db.SetMaxOpenConns(1)

	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) migrate() error {
	const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER NOT NULL,
	isbn   TEXT    NOT NULL
);`
	_, err := s.db.Exec(schema)
	return err
}

// Close releases the underlying database resources.
func (s *Store) Close() error {
	return s.db.Close()
}

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(b Book) (Book, error) {
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

// List returns all books. If author is non-empty, only books by that author
// are returned.
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

// Get returns the book with the given ID, or ErrNotFound.
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

// Update replaces the book with the given ID. It returns ErrNotFound if no
// such book exists.
func (s *Store) Update(id int64, b Book) (Book, error) {
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

// Delete removes the book with the given ID. It returns ErrNotFound if no such
// book exists.
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
