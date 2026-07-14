package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("BOOKS_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("BOOKS_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	st, err := openStore(dsn)
	if err != nil {
		log.Fatalf("open store: %v", err)
	}
	defer st.Close()

	srv := newServer(st)
	log.Printf("listening on %s (db=%s)", addr, dsn)
	if err := http.ListenAndServe(addr, srv.routes()); err != nil {
		log.Fatalf("server: %v", err)
	}
}
