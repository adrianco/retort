package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
)

// Book is a book stored by the service.
type Book struct {
	ID int64 `json:"id"`
	BookInput
}

// BookInput is the client-supplied part of a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type bookScanner interface {
	Scan(dest ...any) error
}

func scanBook(scanner bookScanner) (Book, error) {
	var book Book
	err := scanner.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	return book, err
}

func parseBookID(path string) (int64, bool) {
	idPart := strings.TrimPrefix(path, "/books/")
	if idPart == "" || strings.Contains(idPart, "/") {
		return 0, false
	}
	id, err := strconv.ParseInt(idPart, 10, 64)
	if err != nil || id < 1 {
		return 0, false
	}
	return id, true
}

func decodeBookInput(r *http.Request) (BookInput, error) {
	decoder := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	decoder.DisallowUnknownFields()
	var input BookInput
	if err := decoder.Decode(&input); err != nil {
		return BookInput{}, fmt.Errorf("invalid JSON request body")
	}
	if err := decoder.Decode(&struct{}{}); err != io.EOF {
		return BookInput{}, fmt.Errorf("request body must contain one JSON object")
	}

	input.Title = strings.TrimSpace(input.Title)
	input.Author = strings.TrimSpace(input.Author)
	input.ISBN = strings.TrimSpace(input.ISBN)
	if input.Title == "" {
		return BookInput{}, fmt.Errorf("title is required")
	}
	if input.Author == "" {
		return BookInput{}, fmt.Errorf("author is required")
	}
	return input, nil
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	// Encoding to a ResponseWriter only fails after response headers are sent.
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func methodNotAllowed(w http.ResponseWriter, allowed ...string) {
	w.Header().Set("Allow", strings.Join(allowed, ", "))
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}
