package main

import (
    "database/sql"
    "log"
    "os"
    _ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

func initDB() *sql.DB {
    if db != nil {
        return db
    }
    dbPath := "books.db"
    // Use env var for test
    if val := os.Getenv("BOOKAPI_DB"); val != "" {
        dbPath = val
    }
    var err error
    db, err = sql.Open("sqlite3", dbPath)
    if err != nil {
        log.Fatalf("failed to open db: %v", err)
    }
    // Create table if not exists
    create := `
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );`
    if _, err := db.Exec(create); err != nil {
        log.Fatalf("failed to create table: %v", err)
    }
    return db
}

func getDB() *sql.DB {
    return initDB()
}

func closeDB() {
    if db != nil {
        db.Close()
    }
}
