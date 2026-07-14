package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

func initDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id      INTEGER PRIMARY KEY AUTOINCREMENT,
		title   TEXT NOT NULL,
		author  TEXT NOT NULL,
		year    INTEGER,
		isbn    TEXT
	)`)
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("create table: %w", err)
	}

	return db, nil
}

func dbCreateBook(db *sql.DB, b *Book) error {
	res, err := db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
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

func dbListBooks(db *sql.DB, author string) ([]Book, error) {
	var rows *sql.Rows
	var err error
	if author != "" {
		rows, err = db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ?`,
			author,
		)
	} else {
		rows, err = db.Query(`SELECT id, title, author, year, isbn FROM books`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func dbGetBook(db *sql.DB, id int64) (*Book, error) {
	row := db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	)
	var b Book
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
		return nil, err
	}
	return &b, nil
}

func dbUpdateBook(db *sql.DB, id int64, b *Book) error {
	res, err := db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return sql.ErrNoRows
	}
	b.ID = id
	return nil
}

func dbDeleteBook(db *sql.DB, id int64) error {
	res, err := db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}
