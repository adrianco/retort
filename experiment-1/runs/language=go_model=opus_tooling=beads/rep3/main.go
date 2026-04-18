package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("DB_DSN")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	store, err := NewStore(dsn)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, srv.Routes()); err != nil {
		log.Fatal(err)
	}
}
