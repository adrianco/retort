package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"

	_ "modernc.org/sqlite"
)

// Book represents a book in the collection.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// DB holds the database connection.
var db *sql.DB

// dbFile is the path to the SQLite database file (overridable for tests).
var dbFile = "books.db"

// initDB opens (or creates) the SQLite database and creates the books table.
func initDB() error {
	var err error
	db, err = sql.Open("sqlite", "file:"+dbFile+"?cache=shared&mode=rwc")
	if err != nil {
		return err
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`
	_, err = db.Exec(createTable)
	return err
}

func main() {
	if err := initDB(); err != nil {
		log.Fatalf("failed to initialize database: %v", err)
	}
	defer db.Close()

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/books", booksHandler)
	http.HandleFunc("/books/", bookHandler)

	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}

// healthHandler responds with a 200 OK for the health check.
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status":"ok"}`)
}
