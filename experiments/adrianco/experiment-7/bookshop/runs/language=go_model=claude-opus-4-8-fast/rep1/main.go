package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("BOOKS_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("BOOKS_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := NewStore(dsn)
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Printf("book API listening on %s (db: %s)", addr, dsn)
	if err := http.ListenAndServe(addr, srv); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
