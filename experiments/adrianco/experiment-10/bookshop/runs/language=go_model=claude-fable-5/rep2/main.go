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
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := NewStore(dsn)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	log.Printf("listening on %s (db: %s)", addr, dsn)
	if err := http.ListenAndServe(addr, NewRouter(store)); err != nil {
		log.Fatal(err)
	}
}
