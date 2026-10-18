package main

import (
	"database/sql"
)

// initDB creates the books table if it does not exist yet.
func initDB(db *sql.DB) error {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id      INTEGER PRIMARY KEY AUTOINCREMENT,
			title   TEXT NOT NULL,
			author  TEXT NOT NULL,
			year    INTEGER,
			isbn    TEXT,
			created_at TEXT NOT NULL DEFAULT (datetime('now'))
		)`)
	return err
}

// getBook loads a single book by ID, returning sql.ErrNoRows when absent.
func getBook(db *sql.DB, id int64) (*Book, error) {
	row := db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	b, err := scanBookRow(row)
	if err != nil {
		return nil, err
	}
	return b, nil
}

// scanBookRow scans a row that has a single column per field (QueryRow).
func scanBookRow(row *sql.Row) (*Book, error) {
	var (
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return nil, err
	}
	applyNullable(&b, year, isbn)
	return &b, nil
}

// scanBook scans a row from a *sql.Rows iterator.
func scanBook(rows *sql.Rows) (Book, error) {
	var (
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := rows.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return b, err
	}
	applyNullable(&b, year, isbn)
	return b, nil
}

func applyNullable(b *Book, year sql.NullInt64, isbn sql.NullString) {
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	b.ISBN = isbn.String
}
