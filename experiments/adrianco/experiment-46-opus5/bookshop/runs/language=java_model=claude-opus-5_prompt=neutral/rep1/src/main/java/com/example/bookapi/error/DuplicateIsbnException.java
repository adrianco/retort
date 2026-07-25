package com.example.bookapi.error;

/** Raised when an ISBN is already used by another book; mapped to HTTP 409. */
public class DuplicateIsbnException extends RuntimeException {

    public DuplicateIsbnException(String isbn) {
        super("A book with isbn " + isbn + " already exists");
    }
}
