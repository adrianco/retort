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
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	log.Printf("listening on %s (db: %s)", addr, dbPath)
	if err := http.ListenAndServe(addr, NewServer(store)); err != nil {
		log.Fatal(err)
	}
}
