package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // registers the pure-Go "sqlite" driver
)

// ErrNotFound is returned when a book with the requested ID does not exist.
var ErrNotFound = errors.New("book not found")

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER,
	isbn   TEXT
);`

// Store persists books in a SQLite database.
type Store struct {
	db *sql.DB
}

// OpenStore opens (creating if necessary) the SQLite database at path and
// ensures the schema exists. Use ":memory:" for a throwaway database.
func OpenStore(path string) (*Store, error) {
	dsn := path + "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite allows a single writer at a time. One shared connection avoids
	// SQLITE_BUSY errors and is required for ":memory:", where every new
	// connection would otherwise see its own empty database.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the underlying database.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Create inserts b and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)
		 RETURNING id, title, author, year, isbn`,
		b.Title, b.Author, b.Year, b.ISBN)
	created, err := scanBook(row)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	return created, nil
}

// List returns all books ordered by ID. If author is non-empty, only books
// whose author contains it (case-insensitive) are returned.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author LIKE ? ESCAPE '\'`
		args = append(args, "%"+escapeLike(author)+"%")
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	return books, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// Update replaces every field of the book with the given ID and returns the
// stored result, or ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?
		 RETURNING id, title, author, year, isbn`,
		b.Title, b.Author, b.Year, b.ISBN, id)
	updated, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	return updated, nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

type scanner interface {
	Scan(dest ...any) error
}

func scanBook(sc scanner) (Book, error) {
	var (
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	if isbn.Valid {
		b.ISBN = &isbn.String
	}
	return b, nil
}

// escapeLike escapes the LIKE wildcards % and _ (and the escape character
// itself) so user input is matched literally.
func escapeLike(s string) string {
	return strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`).Replace(s)
}
