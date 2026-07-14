package main

import (
	"flag"
	"log"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	dbPath := flag.String("db", "books.db", "Path to SQLite database file")
	flag.Parse()

	if v := os.Getenv("ADDR"); v != "" {
		*addr = v
	}
	if v := os.Getenv("DB_PATH"); v != "" {
		*dbPath = v
	}

	store, err := OpenStore(*dbPath)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	srv := NewServer(store)
	log.Printf("books API listening on %s (db=%s)", *addr, *dbPath)
	if err := http.ListenAndServe(*addr, srv.Routes()); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
