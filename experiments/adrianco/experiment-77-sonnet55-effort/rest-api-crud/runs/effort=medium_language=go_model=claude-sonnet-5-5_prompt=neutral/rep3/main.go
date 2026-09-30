package main

import (
	"log"
	"net/http"
	"os"
)

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func main() {
	store, err := NewStore(getenv("DB_PATH", "books.db"))
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	addr := getenv("ADDR", ":8080")
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, NewHandler(store)))
}
