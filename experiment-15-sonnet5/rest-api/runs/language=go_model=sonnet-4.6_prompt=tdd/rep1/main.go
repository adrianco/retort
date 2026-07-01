package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "books.db"
	}

	s, err := newSQLiteStore(dsn)
	if err != nil {
		log.Fatalf("open store: %v", err)
	}
	defer s.close()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("listening on :%s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, newRouter(s)))
}
