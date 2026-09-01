package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

// Book is the API and storage representation of a book.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      *int      `json:"year,omitempty"`
	ISBN      string    `json:"isbn,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput is the client-supplied payload for create and update.
type BookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// ErrNotFound is returned when a book ID does not exist.
var ErrNotFound = errors.New("book not found")

// ErrDuplicateISBN is returned when a non-empty ISBN is already in use.
var ErrDuplicateISBN = errors.New("isbn already exists")

// Store wraps the SQLite database.
type Store struct {
	db *sql.DB
}

// OpenStore opens (or creates) a SQLite database at path and applies the schema.
// Use ":memory:" for an ephemeral in-process database.
func OpenStore(path string) (*Store, error) {
	dsn := path
	if path == ":memory:" {
		// A shared-cache in-memory DB keeps one database across pool connections.
		dsn = "file::memory:?cache=shared"
	}
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite handles one writer at a time; a single connection avoids
	// SQLITE_BUSY errors and keeps in-memory databases consistent.
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
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT NOT NULL,
	author     TEXT NOT NULL,
	year       INTEGER,
	isbn       TEXT,
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique ON books(isbn) WHERE isbn <> '';
CREATE INDEX IF NOT EXISTS books_author_idx ON books(author);
`
	if _, err := s.db.Exec(schema); err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

const bookColumns = "id, title, author, year, isbn, created_at, updated_at"

func scanBook(sc interface{ Scan(...any) error }) (Book, error) {
	var (
		b       Book
		year    sql.NullInt64
		isbn    sql.NullString
		created string
		updated string
	)
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn, &created, &updated); err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	b.ISBN = isbn.String
	b.CreatedAt, _ = time.Parse(time.RFC3339Nano, created)
	b.UpdatedAt, _ = time.Parse(time.RFC3339Nano, updated)
	return b, nil
}

func isUniqueViolation(err error) bool {
	return err != nil && strings.Contains(err.Error(), "UNIQUE constraint failed")
}

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, title, author string, year *int, isbn string) (Book, error) {
	now := time.Now().UTC()
	ts := now.Format(time.RFC3339Nano)
	res, err := s.db.ExecContext(ctx,
		"INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
		title, author, nullableInt(year), isbn, ts, ts)
	if err != nil {
		if isUniqueViolation(err) {
			return Book{}, ErrDuplicateISBN
		}
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("last insert id: %w", err)
	}
	return s.Get(ctx, id)
}

// Get returns a single book by ID.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx, "SELECT "+bookColumns+" FROM books WHERE id = ?", id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// List returns all books, optionally filtered by exact (case-insensitive) author.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := "SELECT " + bookColumns + " FROM books"
	var args []any
	if author != "" {
		query += " WHERE author = ? COLLATE NOCASE"
		args = append(args, author)
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
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// Update replaces the mutable fields of an existing book.
func (s *Store) Update(ctx context.Context, id int64, title, author string, year *int, isbn string) (Book, error) {
	ts := time.Now().UTC().Format(time.RFC3339Nano)
	res, err := s.db.ExecContext(ctx,
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?",
		title, author, nullableInt(year), isbn, ts, id)
	if err != nil {
		if isUniqueViolation(err) {
			return Book{}, ErrDuplicateISBN
		}
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	return s.Get(ctx, id)
}

// Delete removes a book by ID.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, "DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func nullableInt(v *int) any {
	if v == nil {
		return nil
	}
	return *v
}
