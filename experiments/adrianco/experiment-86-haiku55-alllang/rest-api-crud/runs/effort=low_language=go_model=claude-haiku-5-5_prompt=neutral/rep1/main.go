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

	store, err := OpenStore(dbPath)
	if err != nil {
		log.Fatalf("open store: %v", err)
	}
	defer store.Close()

	log.Printf("bookapi listening on %s (db: %s)", addr, dbPath)
	if err := http.ListenAndServe(addr, NewServer(store)); err != nil {
		log.Fatalf("server: %v", err)
	}
}
