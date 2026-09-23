package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"strings"
	"time"

	"modernc.org/sqlite"
	sqlite3 "modernc.org/sqlite/lib"
)

var (
	// ErrNotFound is returned when no book has the requested ID.
	ErrNotFound = errors.New("book not found")
	// ErrDuplicateISBN is returned when another book already has the ISBN.
	ErrDuplicateISBN = errors.New("a book with this ISBN already exists")
)

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER,
	isbn       TEXT,
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique ON books (isbn);
`

const bookColumns = "id, title, author, year, isbn, created_at, updated_at"

// Store persists books in a SQLite database.
type Store struct {
	db  *sql.DB
	now func() time.Time
}

// OpenStore opens (creating if necessary) the SQLite database at path and
// applies the schema. The special path ":memory:" gives a private in-memory
// database that lives as long as the Store.
func OpenStore(path string) (*Store, error) {
	params := url.Values{}
	params.Add("_pragma", "busy_timeout(5000)")
	memory := path == ":memory:"
	if !memory {
		params.Add("_pragma", "journal_mode(WAL)")
		params.Add("_pragma", "synchronous(NORMAL)")
	}

	db, err := sql.Open("sqlite", "file:"+path+"?"+params.Encode())
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	if memory {
		// Every connection to :memory: is a separate database, so pin the
		// pool to a single long-lived connection.
		db.SetMaxOpenConns(1)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db, now: time.Now}, nil
}

// Close releases the database.
func (s *Store) Close() error { return s.db.Close() }

// Ping checks that the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a new book. in must already be normalized.
func (s *Store) Create(ctx context.Context, in BookInput) (Book, error) {
	ts := formatTime(s.now())
	row := s.db.QueryRowContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at)
		 VALUES (?, ?, ?, ?, ?, ?)
		 RETURNING `+bookColumns,
		in.Title, in.Author, in.Year, in.ISBN, ts, ts)
	b, err := scanBook(row)
	if err != nil {
		return Book{}, translateError(err)
	}
	return b, nil
}

// ListFilter narrows the result of List. Zero values mean "no filter".
type ListFilter struct {
	// Author matches books whose author contains this text, ignoring ASCII case.
	Author string
}

// List returns the books matching f ordered by ID. It never returns a nil slice.
func (s *Store) List(ctx context.Context, f ListFilter) ([]Book, error) {
	query := "SELECT " + bookColumns + " FROM books"
	var args []any
	if f.Author != "" {
		query += ` WHERE author LIKE ? ESCAPE '\'`
		args = append(args, "%"+escapeLike(f.Author)+"%")
	}
	query += " ORDER BY id"

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("list books: %w", err)
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
	row := s.db.QueryRowContext(ctx, "SELECT "+bookColumns+" FROM books WHERE id = ?", id)
	b, err := scanBook(row)
	if err != nil {
		return Book{}, translateError(err)
	}
	return b, nil
}

// Update replaces every client-editable field of the book with the given ID.
// in must already be normalized. It returns ErrNotFound if there is no such book.
func (s *Store) Update(ctx context.Context, id int64, in BookInput) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
		 WHERE id = ?
		 RETURNING `+bookColumns,
		in.Title, in.Author, in.Year, in.ISBN, formatTime(s.now()), id)
	b, err := scanBook(row)
	if err != nil {
		return Book{}, translateError(err)
	}
	return b, nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, "DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

type rowScanner interface {
	Scan(dest ...any) error
}

func scanBook(sc rowScanner) (Book, error) {
	var (
		b                Book
		year             sql.NullInt64
		isbn             sql.NullString
		created, updated string
	)
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn, &created, &updated); err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	if isbn.Valid {
		b.ISBN = &isbn.String
	}
	var err error
	if b.CreatedAt, err = time.Parse(time.RFC3339Nano, created); err != nil {
		return Book{}, fmt.Errorf("parse created_at of book %d: %w", b.ID, err)
	}
	if b.UpdatedAt, err = time.Parse(time.RFC3339Nano, updated); err != nil {
		return Book{}, fmt.Errorf("parse updated_at of book %d: %w", b.ID, err)
	}
	return b, nil
}

func translateError(err error) error {
	if errors.Is(err, sql.ErrNoRows) {
		return ErrNotFound
	}
	var se *sqlite.Error
	if errors.As(err, &se) && se.Code() == sqlite3.SQLITE_CONSTRAINT_UNIQUE {
		return ErrDuplicateISBN
	}
	return err
}

func formatTime(t time.Time) string { return t.UTC().Format(time.RFC3339Nano) }

// escapeLike escapes the LIKE wildcards in s so they match literally.
func escapeLike(s string) string {
	return strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`).Replace(s)
}
