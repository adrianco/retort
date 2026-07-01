package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("BOOKAPI_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	store, err := NewStore(dsn)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	addr := os.Getenv("BOOKAPI_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	api := NewAPI(store)
	log.Printf("listening on %s (db: %s)", addr, dsn)
	if err := http.ListenAndServe(addr, api.Routes()); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
