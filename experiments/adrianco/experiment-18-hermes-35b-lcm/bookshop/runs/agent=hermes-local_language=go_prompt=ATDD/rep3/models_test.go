package main

import (
	"errors"
	"testing"
)

func TestModel_ValidateTitleRequired(t *testing.T) {
	book := Book{Title: "", Author: "Author"}
	if err := book.Validate(); err == nil {
		t.Fatal("expected validation error for empty title")
	} else if err.Error() != "title is required" {
		t.Errorf("expected 'title is required', got %q", err.Error())
	}
}

func TestModel_ValidateAuthorRequired(t *testing.T) {
	book := Book{Title: "Title", Author: ""}
	if err := book.Validate(); err == nil {
		t.Fatal("expected validation error for empty author")
	} else if err.Error() != "author is required" {
		t.Errorf("expected 'author is required', got %q", err.Error())
	}
}

func TestModel_ValidatePassesWhenBothFieldsSet(t *testing.T) {
	book := Book{Title: "Title", Author: "Author"}
	if err := book.Validate(); err != nil {
		t.Errorf("expected no error, got %v", err)
	}
}

func TestModel_ValidateRequiresBothFields(t *testing.T) {
	book := Book{Title: "", Author: ""}
	err := book.Validate()
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, nil) {
		// Just check it returns a non-nil error
	}
}
