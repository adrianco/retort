package main

import (
	"testing"
)

// Unit tests for Book validation (ATDD: validation layer)

func TestValidate_ValidBook(t *testing.T) {
	book := &Book{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	err := book.Validate()
	if err != nil {
		t.Errorf("expected no error for valid book, got: %v", err)
	}
}

func TestValidate_MissingTitle(t *testing.T) {
	book := &Book{
		Title:  "",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	err := book.Validate()
	if err == nil {
		t.Fatal("expected error for missing title, got nil")
	}

	validationErr, ok := err.(*BookValidationErrors)
	if !ok {
		t.Fatalf("expected *BookValidationErrors, got %T", err)
	}
	if validationErr.Title == "" {
		t.Error("expected title error message, got empty string")
	}
	if validationErr.Author != "" {
		t.Error("expected no author error, got:", validationErr.Author)
	}
}

func TestValidate_MissingAuthor(t *testing.T) {
	book := &Book{
		Title:  "The Go Programming Language",
		Author: "",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	err := book.Validate()
	if err == nil {
		t.Fatal("expected error for missing author, got nil")
	}

	validationErr, ok := err.(*BookValidationErrors)
	if !ok {
		t.Fatalf("expected *BookValidationErrors, got %T", err)
	}
	if validationErr.Author == "" {
		t.Error("expected author error message, got empty string")
	}
	if validationErr.Title != "" {
		t.Error("expected no title error, got:", validationErr.Title)
	}
}

func TestValidate_BothMissing(t *testing.T) {
	book := &Book{
		Title:  "",
		Author: "",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	err := book.Validate()
	if err == nil {
		t.Fatal("expected error when both title and author are missing, got nil")
	}

	validationErr, ok := err.(*BookValidationErrors)
	if !ok {
		t.Fatalf("expected *BookValidationErrors, got %T", err)
	}
	if validationErr.Title == "" {
		t.Error("expected title error")
	}
	if validationErr.Author == "" {
		t.Error("expected author error")
	}
}

func TestError_StringOutput(t *testing.T) {
	err := &BookValidationErrors{
		Title:  "title is required",
		Author: "author is required",
	}

	msg := err.Error()
	if msg == "" {
		t.Error("expected error message to be non-empty")
	}
}
