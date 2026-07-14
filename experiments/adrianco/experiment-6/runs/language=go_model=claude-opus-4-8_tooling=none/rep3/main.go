package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("DB_PATH")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := NewStore(dsn)
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)

	log.Printf("listening on %s (db: %s)", addr, dsn)
	if err := http.ListenAndServe(addr, srv.Routes()); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
