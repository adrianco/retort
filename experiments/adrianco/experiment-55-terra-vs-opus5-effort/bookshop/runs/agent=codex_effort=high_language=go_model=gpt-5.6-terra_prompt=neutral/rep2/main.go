package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"

	_ "modernc.org/sqlite"
)

func main() {
	databasePath := os.Getenv("DATABASE_PATH")
	if databasePath == "" {
		databasePath = "books.db"
	}

	db, err := OpenDatabase(databasePath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer db.Close()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("book API listening on :%s", port)
	if err := http.ListenAndServe(":"+port, NewServer(db)); err != nil {
		log.Fatal(err)
	}
}

// OpenDatabase opens a SQLite database and ensures the schema is present.
func OpenDatabase(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL DEFAULT 0,
			isbn TEXT NOT NULL DEFAULT ''
		)`); err != nil {
		db.Close()
		return nil, fmt.Errorf("create books table: %w", err)
	}
	return db, nil
}
