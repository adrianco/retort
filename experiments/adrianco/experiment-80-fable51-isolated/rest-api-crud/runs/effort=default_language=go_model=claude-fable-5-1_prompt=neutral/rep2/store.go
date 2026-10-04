package main

import (
	"context"
	"database/sql"
	"errors"
	"strings"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book with the requested ID does not exist.
var ErrNotFound = errors.New("book not found")

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT NOT NULL,
	author TEXT NOT NULL,
	year   INTEGER NOT NULL DEFAULT 0,
	isbn   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);`

// NewStore opens (creating if needed) the SQLite database at dsn and ensures
// the schema exists. Use ":memory:" for an ephemeral database.
func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	// Each connection to an in-memory database sees its own private database,
	// so the pool must be limited to a single connection in that case.
	if strings.Contains(dsn, ":memory:") {
		db.SetMaxOpenConns(1)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return Book{}, err
	}
	if b.ID, err = res.LastInsertId(); err != nil {
		return Book{}, err
	}
	return b, nil
}

// List returns all books ordered by ID. If author is non-empty, only books by
// that author (case-insensitive exact match) are returned.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
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

func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	var b Book
	err := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	return b, err
}

func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
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

func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
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
