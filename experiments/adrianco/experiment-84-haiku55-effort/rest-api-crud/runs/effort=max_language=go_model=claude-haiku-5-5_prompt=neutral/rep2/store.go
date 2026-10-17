package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // registers the "sqlite" driver with database/sql
)

// ErrNotFound is returned when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

const (
	schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT NOT NULL,
	author TEXT NOT NULL,
	year   INTEGER,
	isbn   TEXT
)`

	selectBooks = `SELECT id, title, author, year, isbn FROM books`
)

// likeEscaper makes a user-supplied filter match literally inside a LIKE pattern.
var likeEscaper = strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)

// Store keeps books in a SQLite database.
type Store struct {
	db *sql.DB
}

// OpenStore opens the SQLite database at path, creating the file and table if
// they do not exist.
func OpenStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite allows one writer at a time. A single connection avoids lock
	// contention inside the service, and it keeps the per-connection PRAGMA
	// below in effect for every query.
	db.SetMaxOpenConns(1)

	for _, stmt := range []string{
		`PRAGMA busy_timeout = 5000`,
		`PRAGMA journal_mode = WAL`,
		schema,
	} {
		if _, err := db.Exec(stmt); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("initialise database %s: %w", path, err)
		}
	}
	return &Store{db: db}, nil
}

// Create stores b under a new ID and returns it.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	// database/sql stores nil pointers as NULL and dereferences the rest.
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("read new book id: %w", err)
	}
	b.ID = id
	return b, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	b, err := scanBook(s.db.QueryRowContext(ctx, selectBooks+` WHERE id = ?`, id))
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns books in ID order. A non-empty author limits the result to books
// whose author contains it, ignoring case for ASCII letters.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := selectBooks
	var args []any
	if author != "" {
		query += ` WHERE author LIKE ? ESCAPE '\'`
		args = append(args, "%"+likeEscaper.Replace(author)+"%")
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{} // non-nil, so an empty collection is encoded as []
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

// Update replaces every field of book id with the values in b and returns the
// stored book, or ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	if err := checkAffected(res); err != nil {
		return Book{}, err
	}
	b.ID = id
	return b, nil
}

// Delete removes book id, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	return checkAffected(res)
}

// Ping reports whether the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Close releases the database.
func (s *Store) Close() error {
	return s.db.Close()
}

// scanner is implemented by both *sql.Row and *sql.Rows.
type scanner interface {
	Scan(dest ...any) error
}

// scanBook reads one row produced by selectBooks. Scanning into **int and
// **string makes NULL columns come back as nil pointers.
func scanBook(row scanner) (Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

// checkAffected returns ErrNotFound when a write matched no row.
func checkAffected(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("count affected rows: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
