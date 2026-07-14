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
	srv, err := NewServer(dbPath)
	if err != nil {
		log.Fatal(err)
	}
	defer srv.Close()

	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, srv.Handler()))
}
