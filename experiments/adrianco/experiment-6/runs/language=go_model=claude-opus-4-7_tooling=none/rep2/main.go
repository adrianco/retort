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
	addr := os.Getenv("BOOKS_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("init store: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Printf("listening on %s (db=%s)", addr, dbPath)
	if err := http.ListenAndServe(addr, srv.Routes()); err != nil {
		log.Fatalf("server: %v", err)
	}
}
