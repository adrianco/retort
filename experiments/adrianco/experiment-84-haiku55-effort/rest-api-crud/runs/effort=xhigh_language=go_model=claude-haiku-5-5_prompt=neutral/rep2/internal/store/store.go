// Package store persists books in an embedded SQLite database.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"bookapi/internal/book"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, registers as "sqlite"
)

// ErrNotFound is returned when no book matches the requested ID.
var ErrNotFound = errors.New("book not found")

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER,
	isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
`

// Store is a book repository backed by a SQLite file.
type Store struct {
	db *sql.DB
}

// Open opens (creating if necessary) the SQLite database file at path and
// applies the schema.
func Open(path string) (*Store, error) {
	// WAL lets readers proceed during writes; busy_timeout makes contention
	// wait rather than fail with SQLITE_BUSY.
	dsn := "file:" + path + "?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)"

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite allows one writer at a time; a single connection keeps the
	// service simple and avoids lock errors.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the database handle.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, nullInt(in.Year), nullString(in.ISBN),
	)
	if err != nil {
		return book.Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return book.Book{}, fmt.Errorf("read new book id: %w", err)
	}
	return fromInput(id, in), nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (book.Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return book.Book{}, ErrNotFound
	}
	if err != nil {
		return book.Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns all books ordered by ID. If author is non-empty, only books
// whose author matches it case-insensitively are returned.
func (s *Store) List(ctx context.Context, author string) ([]book.Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author COLLATE NOCASE = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := make([]book.Book, 0)
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return books, nil
}

// Update replaces the fields of the book with the given ID and returns the
// updated book, or ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, nullInt(in.Year), nullString(in.ISBN), id,
	)
	if err != nil {
		return book.Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	if err := requireOneRow(res); err != nil {
		return book.Book{}, err
	}
	return fromInput(id, in), nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	return requireOneRow(res)
}

// rowScanner is satisfied by both *sql.Row and *sql.Rows.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanBook(r rowScanner) (book.Book, error) {
	var (
		b    book.Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := r.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return book.Book{}, err
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

func requireOneRow(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("read rows affected: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func fromInput(id int64, in book.Input) book.Book {
	return book.Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}

// nullInt and nullString map optional fields to SQL NULL when unset.
func nullInt(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}

func nullString(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}
