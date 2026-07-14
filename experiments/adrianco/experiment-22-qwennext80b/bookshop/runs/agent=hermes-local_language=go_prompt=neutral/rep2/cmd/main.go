package main

import (
	"log"
	"net/http"
	"os"

	"book-api/internal/handler"
	"book-api/internal/migrate"
	"book-api/internal/model"

	"github.com/gorilla/mux"
	_ "github.com/mattn/go-sqlite3"
	"database/sql"
)

func main() {
	db, err := OpenDatabase("books.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	if err := migrate.Migrate(db); err != nil {
		log.Fatal(err)
	}

	bookStore := model.NewBookStore(db)
	h := handler.NewBookHandler(bookStore)

	r := mux.NewRouter()
	r.HandleFunc("/health", h.HealthCheck).Methods("GET")
	r.HandleFunc("/books", h.ListBooks).Methods("GET")
	r.HandleFunc("/books", h.CreateBook).Methods("POST")
	r.HandleFunc("/books/{id}", h.GetBook).Methods("GET")
	r.HandleFunc("/books/{id}", h.UpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", h.DeleteBook).Methods("DELETE")

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}

func OpenDatabase(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	return db, nil
}
