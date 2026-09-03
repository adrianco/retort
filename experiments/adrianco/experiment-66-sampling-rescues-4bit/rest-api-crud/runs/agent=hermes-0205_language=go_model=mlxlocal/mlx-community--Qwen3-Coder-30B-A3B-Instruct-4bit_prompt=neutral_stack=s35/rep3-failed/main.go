package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	_ "github.com/mattn/go-sqlite3"
)

// Book represents a book in our collection
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var db *sql.DB

func init() {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}

	// Create tables if they don't exist
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
	 author TEXT NOT NULL,
	 year INTEGER,
	 isbn TEXT UNIQUE
	)`)

	if err != nil {
		log.Fatal("Failed to create table:", err)
	}
}

func main() {
	// Create router
 router := mux.NewRouter()

	// Define routes
 router.HandleFunc("/health", healthCheck).Methods("GET")
 router.HandleFunc("/books", createBook).Methods("POST")
 router.HandleFunc("/books", getAllBooks).Methods("GET")
 router.HandleFunc("/books/{id}", getBook).Methods("GET")
 router.HandleFunc("/books/{id}", updateBook).Methods("PUT")
 router.HandleFunc("/books/{id}", deleteBook).Methods("DELETE")

	// Start server
 server := &http.Server{
		Addr: "localhost:8080",
		Handler: router,
	}

	// Graceful shutdown signal
 sigChan := make(chan os.Signal, 1)
 signal.Notify(sigChan, syscall.SIGTERM, syscall.SIGINT)

 go func() {
	 log.Println("Server starting on port 8080")
	 if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		 log.Fatal("Server failed to start:", err)
	 }
 }()

 sig := <-sigChan
 log.Println("Shutting down server gracefully...")
}