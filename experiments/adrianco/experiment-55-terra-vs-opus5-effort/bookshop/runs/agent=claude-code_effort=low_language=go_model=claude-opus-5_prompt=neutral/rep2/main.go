package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	dsn := os.Getenv("DB_PATH")
	if dsn == "" {
		dsn = "books.db"
	}

	store, err := OpenStore(dsn)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	log.Printf("listening on %s (db: %s)", addr, dsn)
	if err := http.ListenAndServe(addr, NewServer(store)); err != nil {
		log.Fatal(err)
	}
}
