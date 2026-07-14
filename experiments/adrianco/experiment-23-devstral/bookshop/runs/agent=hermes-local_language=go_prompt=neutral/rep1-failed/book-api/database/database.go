package database

import (
    "database/sql"
    "log"
    
    _ "github.com/mattn/go-sqlite3"
)

var DB *sql.DB

func InitDatabase() {
    db, err := sql.Open("sqlite3", "./books.db")
    if err != nil {
        log.Fatal(err)
    }
    DB = db
    
    // Create table if not exists
    createTableQuery := `
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    );
    `
    _, err = DB.Exec(createTableQuery)
    if err != nil {
        log.Fatal(err)
    }
}

func CloseDatabase() {
    if DB != nil {
        DB.Close()
    }
}
