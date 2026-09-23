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
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatal(err)
	}
	defer store.Close()
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, NewServer(store)))
}
