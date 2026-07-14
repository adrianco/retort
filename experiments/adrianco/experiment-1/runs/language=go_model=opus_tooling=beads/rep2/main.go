package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}
	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("store: %v", err)
	}
	defer store.Close()

	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, NewServer(store)); err != nil {
		log.Fatal(err)
	}
}
