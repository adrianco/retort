package main

import (
	"fmt"
	"log"
	"net/http"
)

func main() {
	db, err := NewDatabase("books.db")
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer db.Close()

	srv := NewServer(db)

	addr := ":8080"
	fmt.Printf("Server listening on %s\n", addr)
	log.Fatal(http.ListenAndServe(addr, srv))
}
