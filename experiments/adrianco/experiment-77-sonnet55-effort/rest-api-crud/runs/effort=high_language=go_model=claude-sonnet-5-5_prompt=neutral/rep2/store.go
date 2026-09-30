package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book does not exist.
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

// OpenStore opens (and migrates) a SQLite database at the given DSN/path.
func OpenStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	// A single connection keeps ":memory:" databases coherent and
	// serialises writes, which is plenty for an embedded DB.
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(`PRAGMA busy_timeout = 5000`); err != nil {
		db.Close()
		return nil, err
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT    NOT NULL,
		author TEXT    NOT NULL,
		year   INTEGER NOT NULL DEFAULT 0,
		isbn   TEXT    NOT NULL DEFAULT ''
	)`); err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

// Ping checks database connectivity.
func (s *Store) Ping() error { return s.db.Ping() }

func (s *Store) Create(b Book) (Book, error) {
	res, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return Book{}, err
	}
	b.ID, err = res.LastInsertId()
	return b, err
}

// List returns all books ordered by ID, optionally filtered by exact author.
func (s *Store) List(author string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		q += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	q += ` ORDER BY id`
	rows, err := s.db.Query(q, args...)
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

func (s *Store) Get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	return b, err
}

func (s *Store) Update(b Book) (Book, error) {
	res, err := s.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, b.ID)
	if err != nil {
		return Book{}, err
	}
	if n, err := res.RowsAffected(); err != nil {
		return Book{}, err
	} else if n == 0 {
		return Book{}, ErrNotFound
	}
	return b, nil
}

func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	if n, err := res.RowsAffected(); err != nil {
		return err
	} else if n == 0 {
		return ErrNotFound
	}
	return nil
}
