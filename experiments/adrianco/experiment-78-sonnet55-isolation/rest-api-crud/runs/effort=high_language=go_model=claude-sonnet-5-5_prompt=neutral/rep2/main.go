// Command bookapi serves a REST API for managing a book collection.
package main

import (
	"flag"
	"log"
	"net/http"
	"os"
	"time"
)

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func main() {
	addr := flag.String("addr", getenv("ADDR", ":8080"), "listen address")
	dbPath := flag.String("db", getenv("DB_PATH", "books.db"), "SQLite database file")
	flag.Parse()

	store, err := NewStore(*dbPath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              *addr,
		Handler:           (&API{store: store}).Handler(),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("listening on %s (db: %s)", *addr, *dbPath)
	log.Fatal(srv.ListenAndServe())
}
