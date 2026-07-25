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
	// ErrNotFound means no book exists with the requested ID.
	ErrNotFound = errors.New("book not found")
	// ErrDuplicateISBN means another book already claims that ISBN.
	ErrDuplicateISBN = errors.New("isbn already exists")
)

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER NOT NULL DEFAULT 0,
	isbn       TEXT,
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);
-- NULL isbn values are treated as distinct by SQLite, so books without an ISBN
-- do not collide with each other.
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique ON books (isbn) WHERE isbn IS NOT NULL;
CREATE INDEX IF NOT EXISTS books_author_idx ON books (author);
`

// Store is the SQLite-backed persistence layer for books.
type Store struct {
	db *sql.DB
	// now is injectable so tests can control timestamps.
	now func() time.Time
}

// OpenStore opens (creating it if needed) the SQLite database at path and
// applies the schema. Use ":memory:" for an ephemeral database.
func OpenStore(ctx context.Context, path string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn(path))
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	// A single writer keeps SQLite happy under concurrent HTTP handlers; WAL
	// mode (set in the DSN) still allows concurrent readers on file databases.
	db.SetMaxOpenConns(1)
	db.SetConnMaxLifetime(0)

	if err := db.PingContext(ctx); err != nil {
		db.Close()
		return nil, fmt.Errorf("connect to database: %w", err)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db, now: time.Now}, nil
}

func dsn(path string) string {
	q := url.Values{}
	q.Add("_pragma", "busy_timeout(5000)")
	q.Add("_pragma", "foreign_keys(1)")
	if path != ":memory:" && !strings.HasPrefix(path, "file::memory:") {
		q.Add("_pragma", "journal_mode(WAL)")
	}
	return path + "?" + q.Encode()
}

// Close releases the underlying database handle.
func (s *Store) Close() error { return s.db.Close() }

// Ping reports whether the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

const bookColumns = "id, title, author, year, isbn, created_at, updated_at"

// Create inserts a new book and returns it with its generated ID and timestamps.
func (s *Store) Create(ctx context.Context, in BookInput) (Book, error) {
	now := s.now().UTC().Truncate(time.Millisecond)
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, nullISBN(in.ISBN), formatTime(now), formatTime(now))
	if err != nil {
		return Book{}, wrapConstraint(err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("read inserted id: %w", err)
	}
	return Book{
		ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN,
		CreatedAt: now, UpdatedAt: now,
	}, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx, `SELECT `+bookColumns+` FROM books WHERE id = ?`, id)
	book, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	return book, err
}

// List returns all books ordered by ID. A non-empty author filters the results
// to books whose author contains it, case-insensitively.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + bookColumns + ` FROM books`
	var args []any
	if author = strings.TrimSpace(author); author != "" {
		query += ` WHERE author LIKE ? ESCAPE '\'`
		args = append(args, "%"+escapeLike(author)+"%")
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		book, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return books, nil
}

// Update replaces every field of an existing book. It returns ErrNotFound if
// the book does not exist, or ErrDuplicateISBN on an ISBN collision.
func (s *Store) Update(ctx context.Context, id int64, in BookInput) (Book, error) {
	now := s.now().UTC().Truncate(time.Millisecond)
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, nullISBN(in.ISBN), formatTime(now), id)
	if err != nil {
		return Book{}, wrapConstraint(err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("read affected rows: %w", err)
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	// Re-read so the response carries the original created_at.
	return s.Get(ctx, id)
}

// Delete removes a book, returning ErrNotFound if it was not there.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("read affected rows: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// scanner is satisfied by both *sql.Row and *sql.Rows.
type scanner interface {
	Scan(dest ...any) error
}

func scanBook(sc scanner) (Book, error) {
	var (
		b                   Book
		isbn                sql.NullString
		createdAt, updateAt string
	)
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &isbn, &createdAt, &updateAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Book{}, err
		}
		return Book{}, fmt.Errorf("scan book: %w", err)
	}
	b.ISBN = isbn.String

	var err error
	if b.CreatedAt, err = parseTime(createdAt); err != nil {
		return Book{}, err
	}
	if b.UpdatedAt, err = parseTime(updateAt); err != nil {
		return Book{}, err
	}
	return b, nil
}

func nullISBN(isbn string) any {
	if isbn == "" {
		return nil
	}
	return isbn
}

// wrapConstraint converts a SQLite UNIQUE violation on books.isbn into
// ErrDuplicateISBN so the HTTP layer can answer 409.
func wrapConstraint(err error) error {
	var sqErr *sqlite.Error
	if errors.As(err, &sqErr) && sqErr.Code() == sqlite3.SQLITE_CONSTRAINT_UNIQUE {
		return ErrDuplicateISBN
	}
	return fmt.Errorf("write book: %w", err)
}

// escapeLike neutralizes LIKE wildcards in user input, paired with ESCAPE '\'.
func escapeLike(s string) string {
	r := strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)
	return r.Replace(s)
}

func formatTime(t time.Time) string { return t.UTC().Format(time.RFC3339Nano) }

func parseTime(s string) (time.Time, error) {
	t, err := time.Parse(time.RFC3339Nano, s)
	if err != nil {
		return time.Time{}, fmt.Errorf("parse timestamp %q: %w", s, err)
	}
	return t.UTC(), nil
}
