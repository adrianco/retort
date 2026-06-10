package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dbPath := os.Getenv("BOOKS_DB")
	if dbPath == "" {
		dbPath = "books.db"
	}
	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer store.Close()

	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	srv := NewServer(store)
	log.Printf("listening on %s (db: %s)", addr, dbPath)
	if err := http.ListenAndServe(addr, srv); err != nil {
		log.Fatal(err)
	}
}
