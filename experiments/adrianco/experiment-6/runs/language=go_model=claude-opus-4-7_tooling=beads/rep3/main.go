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

	store, err := OpenStore(dsn)
	if err != nil {
		log.Fatalf("open store: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Printf("listening on %s (db=%s)", addr, dsn)
	if err := http.ListenAndServe(addr, srv); err != nil {
		log.Fatalf("listen: %v", err)
	}
}
