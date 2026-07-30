package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a requested book does not exist.
var ErrNotFound = errors.New("book not found")

// Book is the representation returned by the API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the request body accepted when creating or replacing a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens a SQLite database at databasePath and creates the books table
// if it has not been created yet.
func NewStore(databasePath string) (*Store, error) {
	db, err := sql.Open("sqlite", databasePath)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	store := &Store{db: db}
	if err := store.init(context.Background()); err != nil {
		db.Close()
		return nil, err
	}

	return store, nil
}

func (s *Store) init(ctx context.Context) error {
	_, err := s.db.ExecContext(ctx, `
		CREATE TABLE IF NOT EXISTS books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL DEFAULT 0,
			isbn TEXT NOT NULL DEFAULT ''
		)
	`)
	if err != nil {
		return fmt.Errorf("create books table: %w", err)
	}
	return nil
}

// Close releases the database connection.
func (s *Store) Close() error {
	return s.db.Close()
}

// Create inserts a book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, input BookInput) (Book, error) {
	result, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		input.Title, input.Author, input.Year, input.ISBN,
	)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("get inserted book ID: %w", err)
	}

	return Book{ID: id, Title: input.Title, Author: input.Author, Year: input.Year, ISBN: input.ISBN}, nil
}

// List returns all books, optionally restricted to an exact author match.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	args := []any(nil)
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := make([]Book, 0)
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

// Get retrieves one book by ID.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	book, err := scanBook(s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	))
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return book, nil
}

// Update replaces the editable fields of a book and returns the new value.
func (s *Store) Update(ctx context.Context, id int64, input BookInput) (Book, error) {
	result, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		input.Title, input.Author, input.Year, input.ISBN, id,
	)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}

	affected, err := result.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("check updated book: %w", err)
	}
	if affected == 0 {
		return Book{}, ErrNotFound
	}

	return Book{ID: id, Title: input.Title, Author: input.Author, Year: input.Year, ISBN: input.ISBN}, nil
}

// Delete removes a book by ID.
func (s *Store) Delete(ctx context.Context, id int64) error {
	result, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}

	affected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("check deleted book: %w", err)
	}
	if affected == 0 {
		return ErrNotFound
	}

	return nil
}

type rowScanner interface {
	Scan(dest ...any) error
}

func scanBook(row rowScanner) (Book, error) {
	var book Book
	if err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
		return Book{}, err
	}
	return book, nil
}
