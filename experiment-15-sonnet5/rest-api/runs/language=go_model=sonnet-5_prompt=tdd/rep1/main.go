package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dbPath := os.Getenv("BOOKAPI_DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	addr := os.Getenv("BOOKAPI_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	router := NewRouter(store)

	log.Printf("listening on %s (db: %s)", addr, dbPath)
	if err := http.ListenAndServe(addr, router); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
