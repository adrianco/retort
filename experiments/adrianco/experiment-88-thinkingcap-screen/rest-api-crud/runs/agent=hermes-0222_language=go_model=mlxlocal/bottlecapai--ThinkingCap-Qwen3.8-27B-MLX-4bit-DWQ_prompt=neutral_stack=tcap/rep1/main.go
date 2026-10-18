package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"
	"strconv"

	_ "modernc.org/sqlite" // pure-Go SQLite driver
)

func main() {
	dbPath := os.Getenv("BOOKS_DB")
	if dbPath == "" {
		dbPath = "books.db"
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		log.Fatalf("open database %s: %v", dbPath, err)
	}
	defer db.Close()

	if err := initDB(db); err != nil {
		log.Fatalf("initialize database: %v", err)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}
	if _, err := strconv.Atoi(port); err != nil {
		log.Fatalf("invalid PORT %q: %v", port, err)
	}

	addr := ":" + port
	log.Printf("book API listening on %s (db: %s)", addr, dbPath)
	if err := http.ListenAndServe(addr, NewHandler(db)); err != nil {
		log.Fatalf("server: %v", err)
	}
}
