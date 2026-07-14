package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var ErrNotFound = errors.New("book not found")

type Store struct {
	db *sql.DB
}

func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`); err != nil {
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) Create(b *Book) error {
	res, err := s.db.Exec(`INSERT INTO books(title, author, year, isbn) VALUES(?,?,?,?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return err
	}
	b.ID = id
	return nil
}

func (s *Store) List(authorFilter string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if authorFilter != "" {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`, authorFilter)
	} else {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	books := make([]Book, 0)
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func (s *Store) Get(id int64) (*Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &b, nil
}

func (s *Store) Update(id int64, b *Book) error {
	res, err := s.db.Exec(`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
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
	b.ID = id
	return nil
}

func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id=?`, id)
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

func (s *Store) Ping() error {
	var n int
	return s.db.QueryRow(`SELECT 1`).Scan(&n)
}

