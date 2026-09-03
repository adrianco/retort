package main

import (
    "database/sql"
    "fmt"
    "log"
)

func main() {
    db, err := sql.Open("sqlite3", "./test.db")
    if err != nil {
        log.Fatal("Failed to open database:", err)
    }
    defer db.Close()

    _, err = db.Exec("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
    if err != nil {
        log.Fatal("Failed to create table:", err)
    }

    fmt.Println("SQLite test successful")
}