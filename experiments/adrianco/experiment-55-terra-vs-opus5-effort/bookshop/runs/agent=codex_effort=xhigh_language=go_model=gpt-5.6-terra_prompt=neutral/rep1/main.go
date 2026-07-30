package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

func main() {
	databasePath := os.Getenv("DATABASE_PATH")
	if databasePath == "" {
		databasePath = "books.db"
	}

	db, err := sql.Open("sqlite3", databasePath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer db.Close()

	server, err := NewServer(db)
	if err != nil {
		log.Fatalf("initialize server: %v", err)
	}

	address := os.Getenv("ADDR")
	if address == "" {
		address = ":8080"
	}

	log.Printf("book API listening on %s", address)
	if err := http.ListenAndServe(address, server); err != nil {
		log.Fatalf("serve HTTP: %v", err)
	}
}
