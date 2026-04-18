package main

import (
	"log"
	"net/http"
	"os"

	_ "modernc.org/sqlite"
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
	if a := os.Getenv("ADDR"); a != "" {
		addr = a
	}
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, srv.Routes()); err != nil {
		log.Fatal(err)
	}
}
