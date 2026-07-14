package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("BOOKAPI_DSN")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("BOOKAPI_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := NewStore(dsn)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Printf("book API listening on %s (db: %s)", addr, dsn)
	if err := http.ListenAndServe(addr, srv); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
