package main

import (
	"log"
	"net/http"
	"os"
	"time"
)

func main() {
	addr := envOr("ADDR", ":8080")
	dbPath := envOr("DB_PATH", "books.db")

	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("open database %q: %v", dbPath, err)
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              addr,
		Handler:           NewHandler(store),
		ReadHeaderTimeout: 10 * time.Second,
	}
	log.Printf("listening on %s (database: %s)", addr, dbPath)
	log.Fatal(srv.ListenAndServe())
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
