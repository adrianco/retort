package main

import (
	"log"
	"net/http"
	"os"
)

func getenv(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func main() {
	s, err := NewServer(getenv("DB_PATH", "books.db"))
	if err != nil {
		log.Fatal(err)
	}
	addr := getenv("ADDR", ":8080")
	log.Println("listening on", addr)
	log.Fatal(http.ListenAndServe(addr, s.Handler()))
}
