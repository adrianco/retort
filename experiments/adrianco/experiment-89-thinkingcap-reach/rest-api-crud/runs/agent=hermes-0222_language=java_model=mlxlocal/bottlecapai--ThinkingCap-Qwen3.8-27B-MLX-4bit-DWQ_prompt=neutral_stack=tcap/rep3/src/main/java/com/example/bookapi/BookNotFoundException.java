package com.example.bookapi;

/** Thrown when a book is not found. Mapped to HTTP 404. */
public class BookNotFoundException extends RuntimeException {

    public BookNotFoundException(String message) {
        super(message);
    }
}
