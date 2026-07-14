package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"

	_ "modernc.org/sqlite"
)

func main() {
	dbPath := os.Getenv("BOOKS_DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer db.Close()

	store, err := NewStore(db)
	if err != nil {
		log.Fatalf("failed to initialize store: %v", err)
	}

	api := NewAPI(store)

	addr := os.Getenv("BOOKS_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	log.Printf("listening on %s (db: %s)", addr, dbPath)
	log.Fatal(http.ListenAndServe(addr, api.Routes()))
}
