// Command bookapi serves a REST API for managing a book collection.
package main

import (
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
	dbPath := getenv("DB_PATH", "books.db")
	addr := getenv("ADDR", ":8080")

	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              addr,
		Handler:           NewHandler(store),
		ReadHeaderTimeout: 10 * time.Second,
	}
	log.Printf("listening on %s (db: %s)", addr, dbPath)
	log.Fatal(srv.ListenAndServe())
}
